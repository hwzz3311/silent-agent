"""
浏览器实例管理器

提供多浏览器实例的注册、获取、注销等功能。
支持依赖注入以便测试。
"""

import logging
from typing import Dict, List, Optional

from .factory import BrowserClientFactory, BrowserMode
from .instance import BrowserInstance

logger = logging.getLogger(__name__)

# 应用级单例（进程内唯一）
_app_manager: Optional['BrowserManager'] = None


class BrowserManager:
    """
    多浏览器实例管理器

    设计: 依赖注入友好，支持应用级单例
    """

    def __init__(self):
        """初始化管理器实例"""
        self._instances: Dict[str, BrowserInstance] = {}
        self._default_instance_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> 'BrowserManager':
        """获取应用级单例（兼容类方法调用）"""
        return get_browser_manager()

    def register_instance(self, instance: BrowserInstance) -> str:
        """
        注册浏览器实例

        Args:
            instance: 浏览器实例

        Returns:
            实例 ID
        """
        self._instances[instance.instance_id] = instance
        # 首次注册设为默认
        if self._default_instance_id is None:
            self._default_instance_id = instance.instance_id
        logger.info(f"[BrowserManager] 注册实例: {instance.instance_id}, 模式: {instance.mode.value}")
        return instance.instance_id

    def get_instance(self, instance_id: Optional[str] = None) -> Optional[BrowserInstance]:
        """
        获取浏览器实例

        Args:
            instance_id: 实例 ID（None 则返回默认实例）

        Returns:
            浏览器实例，不存在则返回 None
        """
        if instance_id is None:
            # 返回默认实例
            if self._default_instance_id:
                return self._instances.get(self._default_instance_id)
            return None

        return self._instances.get(instance_id)

    def unregister_instance(self, instance_id: str) -> bool:
        """
        注销实例并关闭客户端

        Args:
            instance_id: 实例 ID

        Returns:
            是否成功注销
        """
        instance = self._instances.get(instance_id)
        if not instance:
            logger.warning(f"[BrowserManager] 实例不存在: {instance_id}")
            return False

        # 关闭客户端
        if instance.client:
            import asyncio
            try:
                asyncio.get_event_loop().run_until_complete(instance.client.close())
            except Exception as e:
                logger.warning(f"[BrowserManager] 关闭客户端失败: {e}")

        # 从字典中移除
        del self._instances[instance_id]

        # 如果是默认实例重置默认
        if self._default_instance_id == instance_id:
            self._default_instance_id = list(self._instances.keys())[0] if self._instances else None

        logger.info(f"[BrowserManager] 已注销实例: {instance_id}")
        return True

    def list_instances(self) -> List[Dict]:
        """
        列出所有实例

        Returns:
            实例信息列表
        """
        return [inst.to_dict() for inst in self._instances.values()]

    async def get_client(self, instance_id: Optional[str] = None):
        """
        获取实例的客户端（自动连接）

        Args:
            instance_id: 实例 ID（None 则使用默认实例）

        Returns:
            浏览器客户端实例
        """
        instance = self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"浏览器实例不存在: {instance_id}")

        # 如果已有客户端且已连接，直接返回
        if instance.client and instance.is_connected:
            return instance.client

        # 创建客户端
        client = BrowserClientFactory.create_client_for_instance(instance)
        instance.client = client

        # 连接
        try:
            await client.connect()
            instance.is_connected = True
            logger.info(f"[BrowserManager] 客户端已连接: {instance.instance_id}")
        except Exception as e:
            logger.warning(f"[BrowserManager] 客户端连接失败: {e}")
            instance.is_connected = False

        return client

    def set_default_instance(self, instance_id: str) -> bool:
        """
        设置默认实例

        Args:
            instance_id: 实例 ID

        Returns:
            是否设置成功
        """
        if instance_id not in self._instances:
            logger.warning(f"[BrowserManager] 设置默认失败，不存在: {instance_id}")
            return False

        self._default_instance_id = instance_id
        logger.info(f"[BrowserManager] 已设置默认实例: {instance_id}")
        return True


# ========== 应用级单例访问器 ==========

def get_browser_manager() -> BrowserManager:
    """获取应用级浏览器管理器单例（推荐使用）"""
    global _app_manager
    if _app_manager is None:
        _app_manager = BrowserManager()
    return _app_manager


def set_browser_manager(manager: BrowserManager) -> None:
    """设置应用级浏览器管理器（用于测试注入 mock）"""
    global _app_manager
    _app_manager = manager


def reset_browser_manager() -> None:
    """重置应用级浏览器管理器（用于测试清理）"""
    global _app_manager
    _app_manager = None


__all__ = [
    "BrowserManager",
    "get_browser_manager",
    "set_browser_manager",
    "reset_browser_manager",
]

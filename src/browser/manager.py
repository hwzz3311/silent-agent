"""
浏览器实例管理器

提供多浏览器实例的注册、获取、注销等功能。
支持依赖注入以便测试。
"""

import logging
from typing import Dict, List, Optional, ClassVar

from .client_factory import BrowserClientFactory, BrowserMode
from .instance import BrowserInstance

logger = logging.getLogger(__name__)


class BrowserManager:
    """多浏览器实例管理器"""

    # 类变量用于向后兼容（存储实际实例的容器）
    _instances: ClassVar[Dict[str, BrowserInstance]] = {}
    _default_instance_id: ClassVar[Optional[str]] = None
    # 注入的模拟管理器（测试用）
    _injected_manager: ClassVar[Optional['BrowserManager']] = None

    @classmethod
    def set_manager(cls, manager: 'BrowserManager') -> None:
        """注入管理器（用于测试）"""
        cls._injected_manager = manager

    @classmethod
    def reset_manager(cls) -> None:
        """重置管理器（用于测试清理）"""
        cls._injected_manager = None
        cls._instances = {}
        cls._default_instance_id = None

    @classmethod
    def register_instance(cls, instance: BrowserInstance) -> str:
        """
        注册浏览器实例

        Args:
            instance: 浏览器实例

        Returns:
            实例 ID
        """
        cls._instances[instance.instance_id] = instance
        # 首次注册设为默认
        if cls._default_instance_id is None:
            cls._default_instance_id = instance.instance_id
        logger.info(f"[BrowserManager] 注册实例: {instance.instance_id}, 模式: {instance.mode.value}")
        return instance.instance_id

    @classmethod
    def get_instance(cls, instance_id: Optional[str] = None) -> Optional[BrowserInstance]:
        """
        获取浏览器实例

        Args:
            instance_id: 实例 ID（None 则返回默认实例）

        Returns:
            浏览器实例，不存在则返回 None
        """
        if instance_id is None:
            # 返回默认实例
            if cls._default_instance_id:
                return cls._instances.get(cls._default_instance_id)
            return None

        return cls._instances.get(instance_id)

    @classmethod
    def unregister_instance(cls, instance_id: str) -> bool:
        """
        注销实例并关闭客户端

        Args:
            instance_id: 实例 ID

        Returns:
            是否成功注销
        """
        instance = cls._instances.get(instance_id)
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
        del cls._instances[instance_id]

        # 如果是默认实例，重置默认
        if cls._default_instance_id == instance_id:
            cls._default_instance_id = list(cls._instances.keys())[0] if cls._instances else None

        logger.info(f"[BrowserManager] 已注销实例: {instance_id}")
        return True

    @classmethod
    def list_instances(cls) -> List[Dict]:
        """
        列出所有实例

        Returns:
            实例信息列表
        """
        return [inst.to_dict() for inst in cls._instances.values()]

    @classmethod
    async def get_client(cls, instance_id: Optional[str] = None):
        """
        获取实例的客户端（自动连接）

        Args:
            instance_id: 实例 ID（None 则使用默认实例）

        Returns:
            浏览器客户端实例
        """
        instance = cls.get_instance(instance_id)
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

    @classmethod
    def set_default_instance(cls, instance_id: str) -> bool:
        """
        设置默认实例

        Args:
            instance_id: 实例 ID

        Returns:
            是否设置成功
        """
        if instance_id not in cls._instances:
            logger.warning(f"[BrowserManager] 设置默认失败，不存在: {instance_id}")
            return False

        cls._default_instance_id = instance_id
        logger.info(f"[BrowserManager] 已设置默认实例: {instance_id}")
        return True


__all__ = ["BrowserManager"]

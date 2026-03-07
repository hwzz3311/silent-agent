"""
业务工具注册表

提供业务工具的注册、发现和管理功能。
"""

from typing import Dict, Optional, Type, List, Set
import logging
import inspect

from pydantic import BaseModel

from .base import BusinessTool
from .site_base import Site

logger = logging.getLogger(__name__)

# 应用级单例（进程内唯一）
_app_registry: Optional['BusinessToolRegistry'] = None


class ToolVersionInfo(BaseModel):
    """
    工具版本信息

    Attributes:
        version: 版本号
        registered_at: 注册时间戳
        enabled: 是否启用
    """
    version: str
    registered_at: float
    enabled: bool = True


class BusinessToolRegistry:
    """
    业务工具注册表

    功能:
    1. 工具注册与注销
    2. 按名称/网站类型查找工具

    设计: 依赖注入友好，支持应用级单例

    Usage:
        # 获取应用级单例（推荐）
        from src.tools.domain.registry import get_registry
        registry = get_registry()

        # 注册工具
        registry.register_by_class(CheckLoginStatusTool)

        # 按名称获取
        tool = registry.get("xhs_check_login_status")

        # 按网站类型获取
        xhs_tools = registry.get_by_site(XiaohongshuSite)
    """

    def __init__(self):
        """初始化注册表实例"""
        # 实例属性（非类变量）
        self._tools: Dict[str, BusinessTool] = {}
        self._tool_versions: Dict[str, ToolVersionInfo] = {}
        self._site_tools: Dict[Type[Site], Dict[str, BusinessTool]] = {}
        self._categories: Dict[str, Set[str]] = {}
        self._name_to_class: Dict[str, Type[BusinessTool]] = {}

        # 初始化默认类别
        for cat in ["login", "publish", "browse", "interact", "general"]:
            self._categories[cat] = set()

        logger.info("BusinessToolRegistry initialized")

    # ========== 核心方法 ==========

    def register(
        self,
        tool: BusinessTool,
        version: str = None,
        enabled: bool = True,
        overwrite: bool = False
    ) -> bool:
        """
        注册业务工具

        Args:
            tool: 工具实例
            version: 版本号（默认使用工具的 version）
            enabled: 是否启用
            overwrite: 是否覆盖已存在的工具

        Returns:
            bool: 是否注册成功
        """
        # 获取工具名称和版本
        tool_name = tool.name
        tool_version = version or tool.version

        # 检查是否已存在
        if tool_name in self._tools and not overwrite:
            logger.warning(f"Tool {tool_name} already registered, skipping")
            return False

        # 注册工具
        self._tools[tool_name] = tool
        self._tool_versions[tool_name] = ToolVersionInfo(
            version=tool_version,
            registered_at=__import__('time').time(),
            enabled=enabled
        )

        # 注册到网站索引
        site_type = getattr(tool, 'site_type', None)
        if site_type and issubclass(site_type, Site):
            if site_type not in self._site_tools:
                self._site_tools[site_type] = {}
            self._site_tools[site_type][tool_name] = tool

        # 注册到类别索引
        category = getattr(tool, 'operation_category', 'general')
        if category not in self._categories:
            self._categories[category] = set()
        self._categories[category].add(tool_name)

        # 保存类引用（用于动态创建实例）
        self._name_to_class[tool_name] = tool.__class__

        logger.info(f"Registered tool: {tool_name} (v{tool_version})")
        return True

    def register_by_class(
        self,
        tool_class: Type[BusinessTool],
        version: str = None,
        enabled: bool = True
    ) -> bool:
        """
        通过类注册工具（自动创建实例）

        Args:
            tool_class: 工具类
            version: 版本号
            enabled: 是否启用

        Returns:
            bool: 是否注册成功
        """
        # 验证是类且是 BusinessTool 的子类
        if not inspect.isclass(tool_class):
            logger.error(f"Cannot register: {tool_class} is not a class")
            return False

        if not issubclass(tool_class, BusinessTool):
            logger.error(f"Cannot register: {tool_class} is not a BusinessTool")
            return False

        # 创建实例并注册
        instance = tool_class()
        return self.register(instance, version, enabled)

    def unregister(self, tool_name: str) -> bool:
        """
        注销工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否注销成功
        """
        if tool_name not in self._tools:
            logger.warning(f"Tool {tool_name} not found, skipping unregister")
            return False

        # 从各处索引中移除
        tool = self._tools.pop(tool_name)
        self._tool_version.pop(tool_name, None)

        # 从网站索引中移除
        site_type = getattr(tool, 'site_type', None)
        if site_type and site_type in self._site_tools:
            self._site_tools[site_type].pop(tool_name, None)

        # 从类别索引中移除
        category = getattr(tool, 'operation_category', 'general')
        if category in self._categories:
            self._categories[category].discard(tool_name)

        # 从类引用中移除
        self._name_to_class.pop(tool_name, None)

        logger.info(f"Unregistered tool: {tool_name}")
        return True

    def get(self, tool_name: str) -> Optional[BusinessTool]:
        """
        获取工具实例

        Args:
            tool_name: 工具名称

        Returns:
            Optional[BusinessTool]: 工具实例，不存在返回 None
        """
        return self._tools.get(tool_name)

    def create_instance(self, tool_name: str) -> Optional[BusinessTool]:
        """
        创建工具实例

        如果工具已注册，会创建新的实例。

        Args:
            tool_name: 工具名称

        Returns:
            Optional[BusinessTool]: 新创建的实例
        """
        tool_class = self._name_to_class.get(tool_name)
        if tool_class:
            return tool_class()
        return None

    # ========== 查找方法 ==========

    def get_by_site(self, site_type: Type[Site]) -> Dict[str, BusinessTool]:
        """
        获取指定网站类型的所有工具

        Args:
            site_type: 网站类型

        Returns:
            Dict[str, BusinessTool]: 工具名称 -> 工具实例的字典
        """
        # 直接匹配
        if site_type in self._site_tools:
            return self._site_tools[site_type].copy()

        # 检查子类
        for registered_site, tools in self._site_tools.items():
            if issubclass(site_type, registered_site):
                return tools.copy()

        return {}

    def get_by_category(self, category: str) -> Dict[str, BusinessTool]:
        """
        获取指定类别的所有工具

        Args:
            category: 操作类别

        Returns:
            Dict[str, BusinessTool]: 工具名称 -> 工具实例的字典
        """
        tool_names = self._categories.get(category, set())
        return {
            name: self._tools[name]
            for name in tool_names
            if name in self._tools
        }

    # ========== 列表方法 ==========

    def list_all(self) -> List[str]:
        """
        列出所有已注册的工具名称

        Returns:
            List[str]: 工具名称列表
        """
        return list(self._tools.keys())

    def list_enabled(self) -> List[str]:
        """
        列出所有已启用的工具名称

        Returns:
            List[str]: 工具名称列表
        """
        return [
            name for name, info in self._tool_version.items()
            if info.enabled
        ]

    def list_by_category(self, category: str) -> List[str]:
        """
        列出指定类别的所有工具名称

        Args:
            category: 操作类别

        Returns:
            List[str]: 工具名称列表
        """
        return list(self._categories.get(category, set()))

    def list_categories(self) -> List[str]:
        """
        列出所有类别

        Returns:
            List[str]: 类别列表
        """
        return list(self._categories.keys())

    def list_sites(self) -> List[Type[Site]]:
        """
        列出所有已注册工具的网站类型

        Returns:
            List[Type[Site]]: 网站类型列表
        """
        return list(self._site_tools.keys())

    # ========== 状态方法 ==========

    def count(self) -> int:
        """
        获取工具总数

        Returns:
            int: 工具数量
        """
        return len(self._tools)

    def is_registered(self, tool_name: str) -> bool:
        """
        检查工具是否已注册

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否已注册
        """
        return tool_name in self._tools


# ========== 应用级单例访问器 ==========

def get_registry() -> BusinessToolRegistry:
    """获取应用级注册表单例（推荐使用）"""
    global _app_registry
    if _app_registry is None:
        _app_registry = BusinessToolRegistry()
    return _app_registry


def set_registry(registry: BusinessToolRegistry) -> None:
    """设置应用级注册表（用于测试注入 mock）"""
    global _app_registry
    _app_registry = registry


def reset_registry() -> None:
    """重置应用级注册表（用于测试清理）"""
    global _app_registry
    _app_registry = None


__all__ = [
    "BusinessToolRegistry",
    "ToolVersionInfo",
    "get_registry",
    "set_registry",
    "reset_registry",
]

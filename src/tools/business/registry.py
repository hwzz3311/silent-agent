"""
业务工具注册表

提供业务工具的注册、发现和管理功能。
"""

from typing import (
    Dict, Optional, Type, List, Set, Any
)
import logging
import inspect

from pydantic import BaseModel

from .base import BusinessTool
from .site_base import Site

logger = logging.getLogger(__name__)


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
    2. 按名称/类别/网站类型查找工具
    3. 工具版本管理
    4. 工具自动发现

    Singleton Pattern: 使用类属性实现单例

    Usage:
        # 注册工具
        BusinessToolRegistry.register(CheckLoginStatusTool())

        # 按名称获取
        tool = BusinessToolRegistry.get("xhs_check_login_status")

        # 按网站类型获取
        xhs_tools = BusinessToolRegistry.get_by_site(XiaohongshuSite)

        # 按类别获取
        login_tools = BusinessToolRegistry.get_by_category("login")
    """

    # 单例实例
    _instance: Optional['BusinessToolRegistry'] = None

    # 工具存储
    _tools: Dict[str, BusinessTool] = {}
    _tool_versions: Dict[str, ToolVersionInfo] = {}
    _site_tools: Dict[Type[Site], Dict[str, BusinessTool]] = {}
    _categories: Dict[str, Set[str]] = {}
    _name_to_class: Dict[str, Type[BusinessTool]] = {}

    def __new__(cls) -> 'BusinessToolRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._tools = {}
        self._tool_versions = {}
        self._site_tools = {}
        self._categories = {}
        self._name_to_class = {}

        # 初始化默认类别
        default_categories = [
            "login",       # 登录相关
            "publish",     # 发布相关
            "browse",      # 浏览相关
            "interact",    # 互动相关
            "general",     # 通用操作
        ]
        for cat in default_categories:
            self._categories[cat] = set()

        self._initialized = True
        logger.info("BusinessToolRegistry initialized")

    # ========== 核心方法 ==========

    @classmethod
    def register(
        cls,
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
        if tool_name in cls._tools and not overwrite:
            logger.warning(f"Tool {tool_name} already registered, skipping")
            return False

        # 注册工具
        cls._tools[tool_name] = tool
        cls._tool_versions[tool_name] = ToolVersionInfo(
            version=tool_version,
            registered_at=__import__('time').time(),
            enabled=enabled
        )

        # 注册到网站索引
        site_type = getattr(tool, 'site_type', None)
        if site_type and issubclass(site_type, Site):
            if site_type not in cls._site_tools:
                cls._site_tools[site_type] = {}
            cls._site_tools[site_type][tool_name] = tool

        # 注册到类别索引
        category = getattr(tool, 'operation_category', 'general')
        if category not in cls._categories:
            cls._categories[category] = set()
        cls._categories[category].add(tool_name)

        # 保存类引用（用于动态创建实例）
        cls._name_to_class[tool_name] = tool.__class__

        logger.info(f"Registered tool: {tool_name} (v{tool_version})")
        return True

    @classmethod
    def register_by_class(
        cls,
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
        return cls.register(instance, version, enabled)

    @classmethod
    def unregister(cls, tool_name: str) -> bool:
        """
        注销工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否注销成功
        """
        if tool_name not in cls._tools:
            logger.warning(f"Tool {tool_name} not found, skipping unregister")
            return False

        # 从各处索引中移除
        tool = cls._tools.pop(tool_name)
        cls._tool_versions.pop(tool_name, None)

        # 从网站索引中移除
        site_type = getattr(tool, 'site_type', None)
        if site_type and site_type in cls._site_tools:
            cls._site_tools[site_type].pop(tool_name, None)

        # 从类别索引中移除
        category = getattr(tool, 'operation_category', 'general')
        if category in cls._categories:
            cls._categories[category].discard(tool_name)

        # 从类引用中移除
        cls._name_to_class.pop(tool_name, None)

        logger.info(f"Unregistered tool: {tool_name}")
        return True

    @classmethod
    def get(cls, tool_name: str) -> Optional[BusinessTool]:
        """
        获取工具实例

        Args:
            tool_name: 工具名称

        Returns:
            Optional[BusinessTool]: 工具实例，不存在返回 None
        """
        return cls._tools.get(tool_name)

    @classmethod
    def get_instance(cls, tool_name: str) -> Optional[BusinessTool]:
        """
        获取工具实例（别名方法）

        Args:
            tool_name: 工具名称

        Returns:
            Optional[BusinessTool]: 工具实例
        """
        return cls.get(tool_name)

    @classmethod
    def create_instance(cls, tool_name: str) -> Optional[BusinessTool]:
        """
        创建工具实例

        如果工具已注册，会创建新的实例。

        Args:
            tool_name: 工具名称

        Returns:
            Optional[BusinessTool]: 新创建的实例
        """
        tool_class = cls._name_to_class.get(tool_name)
        if tool_class:
            return tool_class()
        return None

    # ========== 查找方法 ==========

    @classmethod
    def get_by_site(cls, site_type: Type[Site]) -> Dict[str, BusinessTool]:
        """
        获取指定网站类型的所有工具

        Args:
            site_type: 网站类型

        Returns:
            Dict[str, BusinessTool]: 工具名称 -> 工具实例的字典
        """
        # 直接匹配
        if site_type in cls._site_tools:
            return cls._site_tools[site_type].copy()

        # 检查子类
        for registered_site, tools in cls._site_tools.items():
            if issubclass(site_type, registered_site):
                return tools.copy()

        return {}

    @classmethod
    def get_by_category(cls, category: str) -> Dict[str, BusinessTool]:
        """
        获取指定类别的所有工具

        Args:
            category: 操作类别

        Returns:
            Dict[str, BusinessTool]: 工具名称 -> 工具实例的字典
        """
        tool_names = cls._categories.get(category, set())
        return {
            name: cls._tools[name]
            for name in tool_names
            if name in cls._tools
        }

    @classmethod
    def get_by_name_pattern(cls, pattern: str) -> Dict[str, BusinessTool]:
        """
        按名称模式查找工具

        Args:
            pattern: 正则表达式模式

        Returns:
            Dict[str, BusinessTool]: 匹配的工具
        """
        import re
        result = {}
        for name, tool in cls._tools.items():
            if re.search(pattern, name, re.IGNORECASE):
                result[name] = tool
        return result

    @classmethod
    def search(cls, query: str) -> Dict[str, BusinessTool]:
        """
        搜索工具（名称、描述、类别）

        Args:
            query: 搜索关键词

        Returns:
            Dict[str, BusinessTool]: 匹配的工具
        """
        query_lower = query.lower()
        result = {}

        for name, tool in cls._tools.items():
            # 检查名称
            if query_lower in name.lower():
                result[name] = tool
                continue

            # 检查描述
            if query_lower in tool.description.lower():
                result[name] = tool
                continue

            # 检查类别
            if query_lower in tool.operation_category.lower():
                result[name] = tool
                continue

        return result

    # ========== 列表方法 ==========

    @classmethod
    def list_all(cls) -> List[str]:
        """
        列出所有已注册的工具名称

        Returns:
            List[str]: 工具名称列表
        """
        return list(cls._tools.keys())

    @classmethod
    def list_enabled(cls) -> List[str]:
        """
        列出所有已启用的工具名称

        Returns:
            List[str]: 工具名称列表
        """
        return [
            name for name, info in cls._tool_versions.items()
            if info.enabled
        ]

    @classmethod
    def list_by_category(cls, category: str) -> List[str]:
        """
        列出指定类别的所有工具名称

        Args:
            category: 操作类别

        Returns:
            List[str]: 工具名称列表
        """
        return list(cls._categories.get(category, set()))

    @classmethod
    def list_categories(cls) -> List[str]:
        """
        列出所有类别

        Returns:
            List[str]: 类别列表
        """
        return list(cls._categories.keys())

    @classmethod
    def list_sites(cls) -> List[Type[Site]]:
        """
        列出所有已注册工具的网站类型

        Returns:
            List[Type[Site]]: 网站类型列表
        """
        return list(cls._site_tools.keys())

    # ========== 状态方法 ==========

    @classmethod
    def count(cls) -> int:
        """
        获取工具总数

        Returns:
            int: 工具数量
        """
        return len(cls._tools)

    @classmethod
    def enabled_count(cls) -> int:
        """
        获取已启用工具数量

        Returns:
            int: 已启用工具数量
        """
        return sum(1 for info in cls._tool_versions.values() if info.enabled)

    @classmethod
    def is_registered(cls, tool_name: str) -> bool:
        """
        检查工具是否已注册

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否已注册
        """
        return tool_name in cls._tools

    @classmethod
    def is_enabled(cls, tool_name: str) -> bool:
        """
        检查工具是否已启用

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否已启用
        """
        info = cls._tool_versions.get(tool_name)
        return info.enabled if info else False

    # ========== 管理方法 ==========

    @classmethod
    def enable(cls, tool_name: str) -> bool:
        """
        启用工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否操作成功
        """
        if tool_name not in cls._tool_versions:
            return False

        cls._tool_versions[tool_name].enabled = True
        logger.info(f"Enabled tool: {tool_name}")
        return True

    @classmethod
    def disable(cls, tool_name: str) -> bool:
        """
        禁用工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否操作成功
        """
        if tool_name not in cls._tool_versions:
            return False

        cls._tool_versions[tool_name].enabled = False
        logger.info(f"Disabled tool: {tool_name}")
        return True

    @classmethod
    def clear(cls) -> int:
        """
        清空所有注册

        Returns:
            int: 清空前工具数量
        """
        count = len(cls._tools)
        cls._tools.clear()
        cls._tool_versions.clear()
        cls._site_tools.clear()
        cls._categories = {cat: set() for cat in cls._categories}
        cls._name_to_class.clear()
        logger.info(f"Cleared {count} tools")
        return count

    @classmethod
    def get_tool_info(cls, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具详细信息

        Args:
            tool_name: 工具名称

        Returns:
            Optional[Dict[str, Any]]: 工具信息字典
        """
        tool = cls._tools.get(tool_name)
        if not tool:
            return None

        version_info = cls._tool_versions.get(tool_name)

        return {
            "name": tool.name,
            "description": tool.description,
            "version": tool.version if version_info else None,
            "enabled": version_info.enabled if version_info else True,
            "site_type": tool.site_type.__name__ if tool.site_type else None,
            "category": tool.operation_category,
            "required_login": tool.required_login,
            "registered_at": version_info.registered_at if version_info else None,
        }

    @classmethod
    def get_all_info(cls) -> List[Dict[str, Any]]:
        """
        获取所有工具信息

        Returns:
            List[Dict[str, Any]]: 工具信息列表
        """
        return [
            cls.get_tool_info(name)
            for name in cls._tools.keys()
        ]

    # ========== 自动发现 ==========

    @classmethod
    def discover_from_module(
        cls,
        module,
        prefix: str = "xhs_",
        enabled: bool = True
    ) -> int:
        """
        从模块自动发现并注册工具

        工具类名必须以 Tool 结尾，且包含 site_type 类属性

        Args:
            module: Python 模块
            prefix: 工具名称前缀
            enabled: 是否启用

        Returns:
            int: 注册的工具数量
        """
        count = 0

        for attr_name in dir(module):
            if attr_name.startswith('_'):
                continue

            attr = getattr(module, attr_name)

            # 检查是否是 BusinessTool 的子类
            if (inspect.isclass(attr) and
                issubclass(attr, BusinessTool) and
                attr is not BusinessTool):

                # 检查是否包含 site_type
                if hasattr(attr, 'site_type') and attr.site_type:
                    # 生成工具名称
                    tool_name = f"{prefix}{attr_name.replace('Tool', '').lower()}"
                    if not tool_name.endswith('_tool'):
                        tool_name = f"{tool_name}_tool"

                    # 注册工具
                    if cls.register_by_class(attr, enabled=enabled):
                        count += 1

        logger.info(f"Discovered {count} tools from module {module.__name__}")
        return count

    @classmethod
    def discover_from_package(
        cls,
        package_name: str,
        prefix: str = "xhs_",
        enabled: bool = True
    ) -> int:
        """
        从包自动发现并注册工具

        Args:
            package_name: 包名称（如 'tools.sites.xiaohongshu'）
            prefix: 工具名称前缀
            enabled: 是否启用

        Returns:
            int: 注册的工具数量
        """
        try:
            import importlib
            package = importlib.import_module(package_name)

            count = 0
            for _, module_name in inspect.getmembers(package, inspect.ismodule):
                count += cls.discover_from_module(
                    module_name,
                    prefix=prefix,
                    enabled=enabled
                )

            return count

        except ImportError as e:
            logger.error(f"Failed to discover from package {package_name}: {e}")
            return 0


# 单例访问便捷函数
business_registry = BusinessToolRegistry()

# 便捷别名
get_tool = BusinessToolRegistry.get
register_tool = BusinessToolRegistry.register
list_tools = BusinessToolRegistry.list_all


__all__ = [
    "BusinessToolRegistry",
    "ToolVersionInfo",
    "business_registry",
    "get_tool",
    "register_tool",
    "list_tools",
]
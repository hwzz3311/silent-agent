"""
业务级 RPA 工具抽象层

提供跨网站可复用的抽象基类和工具。

模块结构:
- site_base.py: 网站适配器抽象基类 (Site, SiteConfig, SiteSelectorSet)
- base.py: 业务工具抽象基类 (BusinessTool)
- registry.py: 工具注册表 (BusinessToolRegistry)
- errors.py: 统一错误处理 (BusinessException, BusinessError)
- logging.py: 业务日志 (BusinessLogger, log_operation)
- selectors/: 选择器管理
    - manager.py: 选择器管理器 (SelectorManager)

Usage:
    # 继承 BusinessTool 实现业务工具
    from tools.business.base import BusinessTool
    from tools.business.site_base import Site

    class MyTool(BusinessTool):
        name = "my_tool"
        description = "我的工具"
        site_type = MySite

    # 注册工具
    from tools.business.registry import BusinessToolRegistry
    BusinessToolRegistry.register(MyTool())
"""

# 抽象基类和装饰器
from .base import BusinessTool, create_business_tool, business_tool
from .site_base import Site, SiteConfig, SiteSelectorSet, PageInfo

# 注册表
from .registry import (
    BusinessToolRegistry,
    ToolVersionInfo,
    get_registry,
    set_registry,
    reset_registry,
)

# 错误处理
from .errors import (
    BusinessErrorCode,
    BusinessError,
    BusinessException,
    ErrorSuggestion,
)

# 日志
from .logging import (
    BusinessLogger,
    log_operation,
    PerformanceLogger,
    PerformanceContext,
    setup_business_logging,
    mask_sensitive_data,
    DEFAULT_SENSITIVE_FIELDS,
)

# 选择器管理 - 通过统一的 src.tools.selector 入口导入
from src.tools.selector import (
    SelectorType,
    SelectorInfo,
    SelectorTestResult,
    SelectorManager,
    GlobalSelectorManager,
    get_selector_manager,
    set_selector_manager,
    reset_selector_manager,
)


__all__ = [
    # 抽象基类
    "BusinessTool",
    "create_business_tool",
    "Site",
    "SiteConfig",
    "SiteSelectorSet",
    "PageInfo",
    # 注册表
    "BusinessToolRegistry",
    "ToolVersionInfo",
    "get_registry",
    "set_registry",
    "reset_registry",
    # 错误处理
    "BusinessErrorCode",
    "BusinessError",
    "BusinessException",
    "ErrorSuggestion",
    # 日志
    "BusinessLogger",
    "log_operation",
    "PerformanceLogger",
    "PerformanceContext",
    "setup_business_logging",
    "mask_sensitive_data",
    "DEFAULT_SENSITIVE_FIELDS",
    # 选择器管理
    "SelectorType",
    "SelectorInfo",
    "SelectorTestResult",
    "SelectorManager",
    "GlobalSelectorManager",
    "get_selector_manager",
    "set_selector_manager",
    "reset_selector_manager",
    # 装饰器
    "business_tool",
]


def setup_logging(level: int = None):
    """
    便捷的日志设置函数

    Args:
        level: 日志级别，默认使用环境变量或 INFO
    """
    import os
    import logging

    if level is None:
        level_str = os.environ.get("LOG_LEVEL", "INFO")
        level = getattr(logging, level_str.upper(), logging.INFO)

    setup_business_logging(level=level)


# 自动发现和注册工具的便捷函数
def discover_and_register(package_name: str, prefix: str = "xhs_") -> int:
    """
    从包自动发现并注册所有工具

    Args:
        package_name: 包名称
        prefix: 工具名称前缀

    Returns:
        int: 注册的工具数量
    """
    return get_registry().discover_from_package(package_name, prefix)


# 版本信息
__version__ = "1.0.0"
__author__ = "Neurone Team"
__description__ = "业务级 RPA 工具抽象层"
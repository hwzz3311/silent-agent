"""
业务工具装饰器

提供 @business_tool 装饰器用于自动注册工具到 BusinessToolRegistry。

Usage:
    from tools.business import business_tool
    from tools.sites.xiaohongshu.adapter import XiaohongshuSite

    @business_tool(name="xhs_check_login_status", site_type=XiaohongshuSite, operation_category="login")
    class CheckLoginStatusTool(BusinessTool[XiaohongshuSite, Params]):
        name = "xhs_check_login_status"  # 可省略，由装饰器设置
        description = "检查小红书登录状态"
        ...
"""

import logging
from typing import Optional, Type, Callable

from .base import BusinessTool
from .registry import BusinessToolRegistry

logger = logging.getLogger(__name__)


def business_tool(
    name: str = None,
    site_type: Type = None,
    operation_category: str = "general",
    version: str = "1.0.0",
    required_login: bool = True,
    enabled: bool = True,
) -> Callable[[Type], Type]:
    """
    业务工具装饰器

    自动注册工具类到 BusinessToolRegistry。

    Args:
        name: 工具名称，如 "xhs_check_login_status"
        site_type: 站点适配器类型，如 XiaohongshuSite
        operation_category: 操作分类，如 "login", "browse", "publish", "interact"
        version: 版本号，默认 "1.0.0"
        required_login: 是否需要登录，默认 True
        enabled: 是否启用注册，默认 True

    Returns:
        装饰器函数

    Usage:
        @business_tool(name="xhs_check_login_status", site_type=XiaohongshuSite, operation_category="login")
        class CheckLoginStatusTool(BusinessTool[XiaohongshuSite, Params]):
            description = "检查小红书登录状态"
            ...
    """
    def decorator(cls: Type) -> Type:
        # 验证类是 BusinessTool 的子类
        if not (isinstance(cls, type) and issubclass(cls, BusinessTool) and cls is not BusinessTool):
            raise TypeError(f"@business_tool 只能用于 BusinessTool 的子类，收到: {cls}")

        # 设置类属性
        if name:
            cls.name = name
        elif not hasattr(cls, 'name') or not cls.name:
            # 从类名自动生成名称
            cls.name = _auto_generate_name(cls)

        cls.operation_category = operation_category
        cls.version = version
        cls.required_login = required_login

        if site_type:
            cls.site_type = site_type

        # 自动注册到注册表
        if enabled:
            BusinessToolRegistry.register_by_class(cls, enabled=True)
            logger.info(f"Registered tool '{cls.name}' via @business_tool decorator")

        return cls

    return decorator


def _auto_generate_name(cls: Type) -> str:
    """
    从类名自动生成工具名称

    例如:
        CheckLoginStatusTool -> xhs_check_login_status
        ListFeedsTool -> xhs_list_feeds
    """
    class_name = cls.__name__

    # 移除 Tool 后缀
    if class_name.endswith('Tool'):
        class_name = class_name[:-4]

    # 转换为蛇形命名
    import re
    name = re.sub(r'(?<!^)([A-Z])', r'_\1', class_name).lower().strip('_')

    return f"{name}_tool"

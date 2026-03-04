"""
工具模块

提供工具工厂、工具注册表和各类工具实现。
"""

from .base import (
    Tool,
    ToolInfo,
    ToolParameters,
    ValidationResult,
    ExecutionContext,
    ToolExecutionLog,
    ToolFactory,
    tool,
)

from .registry import (
    ToolRegistry,
    ToolMetadata,
    ToolCategory,
    default_registry,
    get_registry,
    register_tool,
    unregister_tool,
    get_tool,
    list_tools,
    search_tools,
    tool as tool_decorator,
)

from .browser import (
    ClickTool,
    ClickParams,
    FillTool,
    FillParams,
    NavigateTool,
    NavigateParams,
    ScrollTool,
    ScrollParams,
    ScreenshotTool,
    ScreenshotParams,
    InjectTool,
    InjectParams,
    EvaluateTool,
    EvaluateParams,
    WaitTool,
    WaitParams,
    ExtractTool,
    ExtractParams,
    KeyboardTool,
    KeyboardParams,
    A11yTreeTool,
    A11yTreeParams,
)

# 自动注册所有内置工具
from .browser import *  # noqa: F401


def register_all_tools():
    """注册所有内置工具"""
    from .browser import (
        ClickTool, FillTool, NavigateTool, ScrollTool,
        ScreenshotTool, InjectTool, EvaluateTool, WaitTool,
        ExtractTool, KeyboardTool, A11yTreeTool,
    )

    ToolFactory.register(ClickTool())
    ToolFactory.register(FillTool())
    ToolFactory.register(NavigateTool())
    ToolFactory.register(ScrollTool())
    ToolFactory.register(ScreenshotTool())
    ToolFactory.register(InjectTool())
    ToolFactory.register(EvaluateTool())
    ToolFactory.register(WaitTool())
    ToolFactory.register(ExtractTool())
    ToolFactory.register(KeyboardTool())
    ToolFactory.register(A11yTreeTool())

    # 同时注册到注册表
    registry = get_registry()
    registry.register_many([
        ClickTool(),
        FillTool(),
        NavigateTool(),
        ScrollTool(),
        ScreenshotTool(),
        InjectTool(),
        EvaluateTool(),
        WaitTool(),
        ExtractTool(),
        KeyboardTool(),
        A11yTreeTool(),
    ])


# 注册工具
register_all_tools()


def register_business_tools():
    """
    注册所有业务工具到 ToolRegistry

    将 BusinessToolRegistry 中的业务工具同步到 ToolRegistry，
    使其可以通过 API 调用。
    """
    from .business.registry import BusinessToolRegistry

    registry = get_registry()

    # 先导入所有业务工具模块，触发自动注册
    # 闲鱼 - 手动注册工具（闲鱼登录模块没有 register 函数）
    try:
        from .sites.xianyu.tools.login.get_cookies import GetCookiesTool
        from .sites.xianyu.tools.login.password_login import PasswordLoginTool
        BusinessToolRegistry.register_by_class(GetCookiesTool)
        BusinessToolRegistry.register_by_class(PasswordLoginTool)
    except Exception as e:
        print(f"[ToolRegistry] Skip xianyu login: {e}")

    try:
        from .sites.xianyu.tools.publish import register as xianyu_publish_register
        xianyu_publish_register()
    except Exception as e:
        print(f"[ToolRegistry] Skip xianyu publish: {e}")

    # 小红书
    try:
        from .sites.xiaohongshu.tools.login import register as xhs_login_register
        xhs_login_register()
    except Exception as e:
        print(f"[ToolRegistry] Skip xhs login: {e}")

    try:
        from .sites.xiaohongshu.tools.publish import register as xhs_publish_register
        xhs_publish_register()
    except Exception as e:
        print(f"[ToolRegistry] Skip xhs publish: {e}")

    try:
        from .sites.xiaohongshu.tools.browse import register as xhs_browse_register
        xhs_browse_register()
    except Exception as e:
        print(f"[ToolRegistry] Skip xhs browse: {e}")

    try:
        from .sites.xiaohongshu.tools.interact import register as xhs_interact_register
        xhs_interact_register()
    except Exception as e:
        print(f"[ToolRegistry] Skip xhs interact: {e}")

    # 获取所有业务工具
    business_tools = BusinessToolRegistry.get_all()
    count = 0

    for tool in business_tools:
        tool_name = tool.name

        # 检查是否已存在
        if registry.exists(tool_name):
            continue

        try:
            # 注册到 ToolRegistry
            registry.register(tool)
            count += 1
        except ValueError:
            # 已存在，跳过
            pass

    print(f"[ToolRegistry] Synced {count} business tools")
    return count


# 注册业务工具
register_business_tools()


__all__ = [
    # Base
    "Tool",
    "ToolInfo",
    "ToolParameters",
    "ValidationResult",
    "ExecutionContext",
    "ToolExecutionLog",
    "ToolFactory",
    "tool",
    # Registry
    "ToolRegistry",
    "ToolMetadata",
    "ToolCategory",
    "default_registry",
    "get_registry",
    "register_tool",
    "unregister_tool",
    "get_tool",
    "list_tools",
    "search_tools",
    "tool_decorator",
    # Browser
    "ClickTool",
    "ClickParams",
    "FillTool",
    "FillParams",
    "NavigateTool",
    "NavigateParams",
    "ScrollTool",
    "ScrollParams",
    "ScreenshotTool",
    "ScreenshotParams",
    "InjectTool",
    "InjectParams",
    "EvaluateTool",
    "EvaluateParams",
    "WaitTool",
    "WaitParams",
    "ExtractTool",
    "ExtractParams",
    "KeyboardTool",
    "KeyboardParams",
    "A11yTreeTool",
    "A11yTreeParams",
    # Functions
    "register_all_tools",
]
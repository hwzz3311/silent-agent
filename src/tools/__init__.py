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
from .base import ToolFactory
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
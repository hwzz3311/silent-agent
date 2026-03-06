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

# 统一使用 domain/registry.py 的 BusinessToolRegistry
from .domain.registry import (
    BusinessToolRegistry,
    get_registry,
    ToolVersionInfo,
)

# Browser tools moved to src/tools/primitives/
# 自动注册所有内置工具
from .primitives import *  # noqa: F401


def register_all_tools():
    """注册所有内置工具"""
    from .primitives import (
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


# 注册工具
register_all_tools()


# 业务工具通过 @business_tool 装饰器自动注册到 BusinessToolRegistry


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
    # Registry (统一使用 BusinessToolRegistry)
    "BusinessToolRegistry",
    "get_registry",
    "ToolVersionInfo",
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
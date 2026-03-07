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
    tool,
)

# 统一使用 domain/registry.py 的 BusinessToolRegistry
from .domain.registry import (
    BusinessToolRegistry,
    get_registry,
    ToolVersionInfo,
)

# 业务工具基类和装饰器
from .domain.base import (
    BusinessTool,
    business_tool,
)

# Browser tools moved to src/tools/primitives/
# 自动注册所有内置工具
from .primitives import *  # noqa: F401


# 业务工具通过 @business_tool 装饰器自动注册到 BusinessToolRegistry
# 导入各站点工具模块以触发自动注册
from .sites import xiaohongshu  # noqa: F401
from .sites import xianyu  # noqa: F401


__all__ = [
    # Base
    "Tool",
    "ToolInfo",
    "ToolParameters",
    "ValidationResult",
    "ExecutionContext",
    "ToolExecutionLog",
    "tool",
    # Registry (统一使用 BusinessToolRegistry)
    "BusinessToolRegistry",
    "get_registry",
    "ToolVersionInfo",
    # Business Tool
    "BusinessTool",
    "business_tool",
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
    "ControlTool",
    "ControlParams",
]
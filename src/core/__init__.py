"""
核心模块

提供基础类型定义、异常类、工具抽象等核心功能。
"""

from .result import (
    Result,
    ResultMeta,
    Error,
    ErrorCode,
    ToolResult,
    A11yTreeResult,
    FlowResult,
    RecordResult,
)

from .context import (
    ExecutionContext,
    ExecutionState,
    VariableScope,
    FlowContext,
    create_context,
)

from .exception import (
    ToolException,
    LoginRequiredException,
    ElementNotFoundException,
    SelectorInvalidException,
    BrowserConnectionException,
    ToolNotFoundException,
    ExecutionTimeoutException,
    ValidationException,
    NavigationException,
    AuthenticationException,
    is_tool_exception,
    get_error_response,
)

__all__ = [
    "Result",
    "ResultMeta",
    "Error",
    "ErrorCode",
    "ToolResult",
    "A11yTreeResult",
    "FlowResult",
    "RecordResult",
    "ExecutionContext",
    "ExecutionState",
    "VariableScope",
    "FlowContext",
    "create_context",
    "ToolException",
    "LoginRequiredException",
    "ElementNotFoundException",
    "SelectorInvalidException",
    "BrowserConnectionException",
    "ToolNotFoundException",
    "ExecutionTimeoutException",
    "ValidationException",
    "NavigationException",
    "AuthenticationException",
    "is_tool_exception",
    "get_error_response",
]
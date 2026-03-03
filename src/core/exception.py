"""
核心异常模块

定义项目统一的异常体系，用于标准化的错误处理。
"""

from typing import Any, Dict, Optional


class ToolException(Exception):
    """
    工具异常基类

    所有项目自定义异常都应继承此类。
    提供统一的错误码、可恢复性标志和详情字典。

    Attributes:
        code: 错误码（用于前端识别错误类型）
        recoverable: 是否可恢复（决定 HTTP 状态码）
        details: 额外详情字典
    """

    code: str = "UNKNOWN"
    recoverable: bool = True
    details: Dict[str, Any] = {}

    def __init__(
        self,
        message: str,
        code: str = None,
        recoverable: bool = True,
        details: Dict[str, Any] = None
    ):
        super().__init__(message)
        self.code = code or self.__class__.__name__.replace("Exception", "").upper()
        self.recoverable = recoverable
        self.details = details or {}

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "error": self.code,
            "message": str(self),
            "details": self.details,
            "recoverable": self.recoverable,
        }


# ========== 业务异常 ==========

class LoginRequiredException(ToolException):
    """
    需要登录异常

    当操作需要登录但用户未登录时抛出。
    """

    def __init__(self, site: str, suggestion: str = None):
        super().__init__(
            message=f"{site} 需要登录",
            code="LOGIN_REQUIRED",
            recoverable=True,
            details={"site": site, "suggestion": suggestion}
        )


class ElementNotFoundException(ToolException):
    """
    元素未找到异常

    当 DOM 元素未找到时抛出。
    """

    def __init__(self, selector: str, reason: str = None):
        super().__init__(
            message=f"元素未找到: {selector}",
            code="ELEMENT_NOT_FOUND",
            recoverable=True,
            details={"selector": selector, "reason": reason}
        )


class SelectorInvalidException(ToolException):
    """
    选择器无效异常

    当 CSS/XPath 选择器格式错误时抛出。
    """

    def __init__(self, selector: str, reason: str):
        super().__init__(
            message=f"无效选择器: {selector}",
            code="SELECTOR_INVALID",
            recoverable=False,
            details={"selector": selector, "reason": reason}
        )


class BrowserConnectionException(ToolException):
    """
    浏览器连接异常

    当浏览器连接失败或断开时抛出。
    """

    def __init__(self, message: str, mode: str = None):
        super().__init__(
            message=message,
            code="BROWSER_NOT_CONNECTED",
            recoverable=True,
            details={"mode": mode}
        )


class ToolNotFoundException(ToolException):
    """
    工具未找到异常

    当请求的工具不存在时抛出。
    """

    def __init__(self, tool_name: str):
        super().__init__(
            message=f"工具未找到: {tool_name}",
            code="TOOL_NOT_FOUND",
            recoverable=False,
            details={"tool_name": tool_name}
        )


class ExecutionTimeoutException(ToolException):
    """
    执行超时异常

    当工具执行超时时抛出。
    """

    def __init__(self, tool_name: str, timeout_ms: int):
        super().__init__(
            message=f"工具 {tool_name} 执行超时 (>{timeout_ms}ms)",
            code="EXECUTION_TIMEOUT",
            recoverable=True,
            details={"tool_name": tool_name, "timeout_ms": timeout_ms}
        )


class ValidationException(ToolException):
    """
    参数验证异常

    当工具参数验证失败时抛出。
    """

    def __init__(self, message: str, errors: list = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            recoverable=True,
            details={"errors": errors or []}
        )


class NavigationException(ToolException):
    """
    导航异常

    当页面导航失败时抛出。
    """

    def __init__(self, url: str, reason: str = None):
        super().__init__(
            message=f"导航失败: {url}",
            code="NAVIGATION_FAILED",
            recoverable=True,
            details={"url": url, "reason": reason}
        )


class AuthenticationException(ToolException):
    """
    认证异常

    当认证失败（登录密码错误等）时抛出。
    """

    def __init__(self, site: str, reason: str = None):
        super().__init__(
            message=f"{site} 认证失败",
            code="AUTHENTICATION_FAILED",
            recoverable=True,
            details={"site": site, "reason": reason}
        )


# ========== 便捷函数 ==========

def is_tool_exception(exc: Exception) -> bool:
    """检查是否是工具异常"""
    return isinstance(exc, ToolException)


def get_error_response(exc: Exception) -> dict:
    """将异常转换为错误响应字典"""
    if isinstance(exc, ToolException):
        return exc.to_dict()
    return {
        "error": "INTERNAL_ERROR",
        "message": str(exc),
        "details": {"type": exc.__class__.__name__},
        "recoverable": False,
    }


__all__ = [
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

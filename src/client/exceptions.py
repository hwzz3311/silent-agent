"""
客户端异常模块

定义 WebSocket 客户端相关的异常类型。
"""



class ClientException(Exception):
    """客户端基础异常"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConnectionError(ClientException):
    """连接异常"""

    def __init__(self, message: str = "连接失败", details: dict = None):
        super().__init__(message, details)


class DisconnectedError(ClientException):
    """已断开连接异常"""

    def __init__(self, message: str = "已断开连接", details: dict = None):
        super().__init__(message, details)


class TimeoutError(ClientException):
    """超时异常"""

    def __init__(self, message: str = "请求超时", details: dict = None):
        super().__init__(message, details)


class ProtocolError(ClientException):
    """协议异常"""

    def __init__(self, message: str = "协议错误", details: dict = None):
        super().__init__(message, details)


class ExtensionNotConnectedError(ClientException):
    """扩展未连接异常"""

    def __init__(self, message: str = "扩展未连接", details: dict = None):
        super().__init__(message, details)


class ToolNotFoundError(ClientException):
    """工具未找到异常"""

    def __init__(self, tool_name: str, details: dict = None):
        super().__init__(f"工具未找到: {tool_name}", details)
        self.tool_name = tool_name


class ExecutionError(ClientException):
    """执行异常"""

    def __init__(self, message: str, tool_name: str = None, recoverable: bool = False, details: dict = None):
        super().__init__(message, details)
        self.tool_name = tool_name
        self.recoverable = recoverable


class MessageParseError(ClientException):
    """消息解析异常"""

    def __init__(self, raw_message: str, details: dict = None):
        super().__init__(f"消息解析失败: {raw_message[:100]}", details)
        self.raw_message = raw_message


__all__ = [
    "ClientException",
    "ConnectionError",
    "DisconnectedError",
    "TimeoutError",
    "ProtocolError",
    "ExtensionNotConnectedError",
    "ToolNotFoundError",
    "ExecutionError",
    "MessageParseError",
]
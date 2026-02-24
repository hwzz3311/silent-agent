"""
统一返回结果模块

提供 Result[T] 泛型类，用于工具执行结果的标准化返回。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar, Optional
from enum import Enum
import json


T = TypeVar('T')


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 通用错误
    SUCCESS = "success"
    UNKNOWN = "unknown"
    VALIDATION_ERROR = "validation_error"

    # 执行错误
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_FAILED = "execution_failed"
    TOOL_NOT_FOUND = "tool_not_found"

    # 浏览器错误
    TAB_NOT_FOUND = "tab_not_found"
    TAB_CLOSED = "tab_closed"
    ELEMENT_NOT_FOUND = "element_not_found"
    ELEMENT_NOT_VISIBLE = "element_not_visible"

    # 网络错误
    CONNECTION_ERROR = "connection_error"
    WEBSOCKET_ERROR = "websocket_error"


@dataclass
class Error:
    """错误信息"""
    code: str
    message: str
    details: Optional[dict] = None
    recoverable: bool = False
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    traceback: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "traceback": self.traceback,
        }

    @classmethod
    def from_exception(cls, exc: Exception, code: ErrorCode = None, recoverable: bool = False) -> 'Error':
        """从异常创建错误对象"""
        import traceback
        return cls(
            code=code.value if code else ErrorCode.UNKNOWN.value,
            message=str(exc),
            details={"exception_class": exc.__class__.__name__},
            recoverable=recoverable,
            exception_type=exc.__class__.__name__,
            exception_message=str(exc),
            traceback=traceback.format_exc() if recoverable else None,
        )

    @classmethod
    def unknown(cls, message: str, details: dict = None) -> 'Error':
        """创建未知错误"""
        return cls(
            code=ErrorCode.UNKNOWN.value,
            message=message,
            details=details,
            recoverable=False,
        )

    @classmethod
    def validation(cls, message: str, details: dict = None) -> 'Error':
        """创建验证错误"""
        return cls(
            code=ErrorCode.VALIDATION_ERROR.value,
            message=message,
            details=details,
            recoverable=True,
        )

    @classmethod
    def execution_timeout(cls, tool_name: str, timeout: int) -> 'Error':
        """创建超时错误"""
        return cls(
            code=ErrorCode.EXECUTION_TIMEOUT.value,
            message=f"工具 {tool_name} 执行超时 (>{timeout}ms)",
            details={"tool": tool_name, "timeout_ms": timeout},
            recoverable=True,
        )

    @classmethod
    def element_not_found(cls, selector: str) -> 'Error':
        """创建元素未找到错误"""
        return cls(
            code=ErrorCode.ELEMENT_NOT_FOUND.value,
            message=f"元素未找到: {selector}",
            details={"selector": selector},
            recoverable=True,
        )

    @classmethod
    def tool_not_found(cls, tool_name: str) -> 'Error':
        """创建工具未找到错误"""
        return cls(
            code=ErrorCode.TOOL_NOT_FOUND.value,
            message=f"工具未找到: {tool_name}",
            details={"tool": tool_name},
            recoverable=False,
        )


@dataclass
class ResultMeta:
    """执行元数据"""
    tool_name: str
    duration_ms: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tab_id: Optional[int] = None
    attempt: int = 1
    extra: Optional[dict] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "tool": self.tool_name,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "tab_id": self.tab_id,
            "attempt": self.attempt,
            "extra": self.extra,
        }


@dataclass
class Result(Generic[T]):
    """
    统一返回结果类

    Attributes:
        success: 是否成功
        data: 返回数据（成功时）
        error: 错误信息（失败时）
        meta: 执行元数据
    """
    success: bool
    data: Optional[T] = None
    error: Optional[Error] = None
    meta: Optional[ResultMeta] = None

    # ========== 工厂方法 ==========

    @classmethod
    def ok(cls, data: T = None, meta: ResultMeta = None) -> 'Result[T]':
        """创建成功结果"""
        return cls(success=True, data=data, meta=meta)

    @classmethod
    def fail(cls, error: Error, meta: ResultMeta = None) -> 'Result[T]':
        """创建失败结果"""
        return cls(success=False, error=error, meta=meta)

    @classmethod
    def from_execution(
        cls,
        success: bool,
        data: T = None,
        error: Error = None,
        tool_name: str = None,
        duration_ms: int = None,
        **extra
    ) -> 'Result[T]':
        """从执行结果创建"""
        meta = None
        if tool_name or duration_ms:
            meta = ResultMeta(
                tool_name=tool_name or "unknown",
                duration_ms=duration_ms or 0,
                extra=extra if extra else None,
            )
        return cls(success=success, data=data, error=error, meta=meta)

    # ========== 转换方法 ==========

    def to_dict(self) -> dict:
        """转换为字典（JSON 可序列化）"""
        result = {
            "success": self.success,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "meta": self.meta.to_dict() if self.meta else None,
        }
        # 移除 None 值
        return {k: v for k, v in result.items() if v is not None}

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    # ========== 实用方法 ==========

    def unwrap(self) -> T:
        """解包数据，成功时返回数据，失败时抛出异常"""
        if self.success:
            if self.data is None:
                raise ValueError("Result is successful but data is None")
            return self.data
        raise self.error or RuntimeError("Result failed without error object")

    def unwrap_or(self, default: T) -> T:
        """解包数据，失败时返回默认值"""
        if self.success:
            return self.data if self.data is not None else default
        return default

    def expect(self, message: str = "Result is not successful") -> T:
        """期望成功，失败时抛出异常"""
        if not self.success:
            raise RuntimeError(message)
        return self.unwrap()

    def is_error(self, code: ErrorCode = None) -> bool:
        """检查是否是错误（可选指定错误码）"""
        if not self.success:
            return True
        if code and self.error:
            return self.error.code == code.value
        return False

    def with_duration(self, duration_ms: int) -> 'Result[T]':
        """设置执行时间"""
        if self.meta is None:
            self.meta = ResultMeta(tool_name="unknown", duration_ms=duration_ms)
        else:
            self.meta = duration_ms if isinstance(self.meta, int) else duration_ms
            if hasattr(self.meta, 'duration_ms'):
                self.meta.duration_ms = duration_ms
        return self

    def with_tool_info(self, tool_name: str, tab_id: int = None) -> 'Result[T]':
        """设置工具信息"""
        if self.meta is None:
            self.meta = ResultMeta(tool_name=tool_name, duration_ms=0, tab_id=tab_id)
        else:
            if hasattr(self.meta, 'tool_name'):
                self.meta.tool_name = tool_name
            if hasattr(self.meta, 'tab_id'):
                self.meta.tab_id = tab_id
        return self

    def merge_duration(self, duration_ms: int) -> 'Result[T]':
        """累加执行时间"""
        if self.meta and hasattr(self.meta, 'duration_ms'):
            self.meta.duration_ms += duration_ms
        return self

    # ========== 类型转换 ==========

    def map(self, func: callable) -> 'Result[Any]':
        """映射数据"""
        if self.success and self.data is not None:
            return Result.ok(func(self.data), self.meta)
        return self  # type: ignore

    def flat_map(self, func: callable) -> 'Result[Any]':
        """平展映射（用于链式操作）"""
        if self.success and self.data is not None:
            result = func(self.data)
            if isinstance(result, Result):
                return result
            return Result.ok(result, self.meta)
        return self  # type: ignore

    def recover(self, func: callable) -> 'Result[T]':
        """错误恢复"""
        if not self.success and self.error:
            result = func(self.error)
            if isinstance(result, Result):
                return result
            return Result.ok(result)
        return self


# ========== 便捷类型别名 ==========

# 工具执行结果
ToolResult = Result[Any]

# 无障碍树结果
A11yTreeResult = Result[dict]

# 流程执行结果
FlowResult = Result[dict]

# 录制数据结果
RecordResult = Result[list]


__all__ = [
    "Result",
    "ResultMeta",
    "Error",
    "ErrorCode",
    "ToolResult",
    "A11yTreeResult",
    "FlowResult",
    "RecordResult",
]
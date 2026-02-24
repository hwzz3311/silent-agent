"""
日志格式化模块

提供多种日志格式化器。
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional


class BaseFormatter(ABC):
    """日志格式化器基类"""

    @abstractmethod
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        ...


class SimpleFormatter(BaseFormatter):
    """简单格式化器"""

    def __init__(self, fmt: str = None):
        self.fmt = fmt or "%(message)s"

    def format(self, record: logging.LogRecord) -> str:
        return self.fmt % record.__dict__


class DetailedFormatter(BaseFormatter):
    """详细格式化器"""

    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger: bool = True,
        include_function: bool = False,
        include_line: bool = True,
    ):
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger = include_logger
        self.include_function = include_function
        self.include_line = include_line

    def format(self, record: logging.LogRecord) -> str:
        parts = []

        if self.include_timestamp:
            parts.append(self._format_timestamp(record.created))

        if self.include_level:
            parts.append(f"[{record.levelname:8}]")

        if self.include_logger:
            parts.append(f"[{record.name}]")

        if self.include_function:
            parts.append(f"[{record.funcName}]")

        if self.include_line:
            parts.append(f"[line {record.lineno}]")

        parts.append(record.getMessage())

        if record.exc_info:
            parts.append(self._format_exception(record.exc_info))

        return " ".join(parts)

    def _format_timestamp(self, timestamp: float) -> str:
        """格式化时间戳"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _format_exception(self, exc_info) -> str:
        """格式化异常信息"""
        if not exc_info:
            return ""

        exc_type, exc_value, exc_tb = exc_info
        lines = ["", "Traceback (most recent call last):"]
        for frame in self._format_traceback(exc_tb):
            lines.append(frame)
        lines.append(f"{exc_type.__name__}: {exc_value}")
        return "\n".join(lines)

    def _format_traceback(self, tb) -> list:
        """格式化回溯信息"""
        lines = []
        while tb:
            frame = tb.tb_frame
            lineno = tb.tb_lineno
            code = frame.f_code
            filename = code.co_filename
            lines.append(f'  File "{filename}", line {lineno}, in {code.co_name}')
            if tb.tb_next:
                lines.append("    ...")
            tb = tb.tb_next
        return lines


class JSONFormatter(BaseFormatter):
    """JSON 格式化器"""

    def __init__(
        self,
        extra_fields: Dict[str, Any] = None,
        include_timestamp: bool = True,
        include_logger: bool = True,
        include_function: bool = True,
    ):
        self.extra_fields = extra_fields or {}
        self.include_timestamp = include_timestamp
        self.include_logger = include_logger
        self.include_function = include_function

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name if self.include_logger else None,
            "module": record.module,
        }

        if self.include_function:
            log_entry["function"] = record.funcName
            log_entry["line"] = record.lineno

        # 添加额外字段
        log_entry.update(self.extra_fields)

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self._format_exception(record.exc_info)

        # 添加上下文信息
        if hasattr(record, "context"):
            log_entry["context"] = record.context

        return json.dumps(log_entry, ensure_ascii=False)

    def _format_timestamp(self, timestamp: float) -> str:
        """格式化时间戳"""
        return datetime.fromtimestamp(timestamp).isoformat()

    def _format_exception(self, exc_info) -> Dict[str, Any]:
        """格式化异常信息"""
        if not exc_info:
            return {}

        exc_type, exc_value, tb = exc_info
        return {
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": self._format_traceback(tb),
        }

    def _format_traceback(self, tb) -> list:
        """格式化回溯信息"""
        lines = []
        while tb:
            frame = tb.tb_frame
            lineno = tb.tb_lineno
            code = frame.f_code
            lines.append({
                "file": code.co_filename,
                "line": lineno,
                "function": code.co_name,
            })
            tb = tb.tb_next
        return lines


class StructuredFormatter(BaseFormatter):
    """结构化格式化器（推荐用于机器解析）"""

    def __init__(self, extra_fields: Dict[str, Any] = None):
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": {
                "id": record.process,
                "name": record.processName,
            },
            "thread": {
                "id": record.thread,
                "name": record.threadName,
            },
        }

        # 添加额外字段
        log_entry.update(self.extra_fields)

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self._format_traceback(record.exc_info[2]),
            }

        # 添加额外属性
        if hasattr(record, "data"):
            log_entry["data"] = record.data

        return json.dumps(log_entry, ensure_ascii=False)

    def _format_traceback(self, tb) -> list:
        """格式化回溯信息"""
        lines = []
        while tb:
            frame = tb.tb_frame
            lineno = tb.tb_lineno
            code = frame.f_code
            lines.append(f'  File "{code.co_filename}", line {lineno}, in {code.co_name}')
            tb = tb.tb_next
        return lines


class ExecutionLogFormatter(BaseFormatter):
    """执行日志格式化器（专用于 RPA 执行记录）"""

    def __init__(self):
        self.execution_id = None
        self.tool_name = None

    def set_execution_context(self, execution_id: str, tool_name: str = None) -> None:
        """设置执行上下文"""
        self.execution_id = execution_id
        self.tool_name = tool_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "execution_id": self.execution_id,
            "tool": self.tool_name,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # 添加执行信息
        if hasattr(record, "step_name"):
            log_entry["step"] = record.step_name

        if hasattr(record, "tool_name"):
            log_entry["tool"] = record.tool_name

        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        if hasattr(record, "result"):
            log_entry["result"] = record.result

        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, ensure_ascii=False)


# ========== 格式化器工厂 ==========

class FormatterFactory:
    """格式化器工厂"""

    _formatters = {
        "simple": SimpleFormatter,
        "detailed": DetailedFormatter,
        "json": JSONFormatter,
        "structured": StructuredFormatter,
        "execution": ExecutionLogFormatter,
    }

    @classmethod
    def create(cls, format_type: str, **kwargs) -> BaseFormatter:
        """创建格式化器"""
        formatter_class = cls._formatters.get(format_type)
        if not formatter_class:
            raise ValueError(f"Unknown formatter type: {format_type}")
        return formatter_class(**kwargs)

    @classmethod
    def get_default(cls, format_type: str = "structured") -> BaseFormatter:
        """获取默认格式化器"""
        return cls.create(format_type)


def get_formatter(format_type: str = "structured", **kwargs) -> BaseFormatter:
    """便捷函数：获取格式化器"""
    return FormatterFactory.create(format_type, **kwargs)


__all__ = [
    "BaseFormatter",
    "SimpleFormatter",
    "DetailedFormatter",
    "JSONFormatter",
    "StructuredFormatter",
    "ExecutionLogFormatter",
    "FormatterFactory",
    "get_formatter",
]
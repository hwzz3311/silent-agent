"""
执行日志模块

提供 RPA 执行日志的专用功能。
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionLogEntry:
    """执行日志条目"""
    id: str
    timestamp: str
    level: str
    execution_id: str
    step_name: Optional[str]
    tool_name: Optional[str]
    message: str
    duration_ms: Optional[int]
    result: Optional[Dict[str, Any]]
    error: Optional[Dict[str, Any]]
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "level": self.level,
            "execution_id": self.execution_id,
            "step_name": self.step_name,
            "tool_name": self.tool_name,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "error": self.error,
            "context": self.context,
        }


class ExecutionLogger:
    """
    执行日志记录器

    专门用于记录 RPA 流程执行的日志。

    Attributes:
        execution_id: 执行 ID
        entries: 日志条目列表
    """

    def __init__(self, execution_id: str = None):
        self.execution_id = execution_id or str(uuid.uuid4())
        self.entries: List[ExecutionLogEntry] = []
        self._start_time = None
        self._current_step = None
        self._step_start_time = None

        # 配置日志记录器
        self._setup_logger()

    def _setup_logger(self) -> None:
        """设置日志记录器"""
        self.logger = logging.getLogger(f"neurone.execution.{self.execution_id}")
        self.logger.setLevel(logging.DEBUG)

        # 确保没有重复处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def start(self) -> None:
        """开始执行日志记录"""
        self._start_time = datetime.utcnow()

    def stop(self) -> None:
        """停止执行日志记录"""
        pass

    def log(
        self,
        level: str,
        message: str,
        step_name: str = None,
        tool_name: str = None,
        duration_ms: int = None,
        result: Dict[str, Any] = None,
        error: Dict[str, Any] = None,
        **context,
    ) -> str:
        """
        记录日志

        Args:
            level: 日志级别
            message: 日志消息
            step_name: 步骤名称
            tool_name: 工具名称
            duration_ms: 持续时间（毫秒）
            result: 执行结果
            error: 错误信息
            **context: 额外上下文

        Returns:
            日志条目 ID
        """
        entry = ExecutionLogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            execution_id=self.execution_id,
            step_name=step_name,
            tool_name=tool_name,
            message=message,
            duration_ms=duration_ms,
            result=result,
            error=error,
            context=context,
        )

        self.entries.append(entry)

        # 同时使用标准日志记录器
        extra = {
            "execution_id": self.execution_id,
            "step_name": step_name,
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "result": result,
        }
        self.logger.log(
            getattr(logging, level.upper()),
            f"[{step_name or 'global'}] {message}",
            extra=extra,
        )

        return entry.id

    def debug(self, message: str, **context) -> str:
        """记录调试日志"""
        return self.log("debug", message, **context)

    def info(self, message: str, **context) -> str:
        """记录信息日志"""
        return self.log("info", message, **context)

    def warning(self, message: str, **context) -> str:
        """记录警告日志"""
        return self.log("warning", message, **context)

    def error(self, message: str, error: Dict[str, Any] = None, **context) -> str:
        """记录错误日志"""
        return self.log("error", message, error=error, **context)

    def step_start(self, step_name: str, tool_name: str = None) -> None:
        """步骤开始"""
        self._current_step = step_name
        self._step_start_time = time.time()

    def step_end(
        self,
        step_name: str = None,
        result: Dict[str, Any] = None,
        success: bool = True,
        error: Exception = None,
    ) -> None:
        """步骤结束"""
        duration_ms = None
        if self._step_start_time:
            duration_ms = int((time.time() - self._step_start_time) * 1000)

        err_info = None
        if error:
            err_info = {
                "type": error.__class__.__name__,
                "message": str(error),
            }

        self.log(
            level="info" if success else "error",
            message=f"步骤 '{step_name or self._current_step}' {'成功' if success else '失败'}",
            step_name=step_name or self._current_step,
            duration_ms=duration_ms,
            result=result,
            error=err_info,
        )

        self._current_step = None
        self._step_start_time = None

    def add_context(self, key: str, value: Any) -> None:
        """添加上下文信息"""
        self.context[key] = value

    def remove_context(self, key: str) -> None:
        """移除上下文信息"""
        self.context.pop(key, None)

    @property
    def context(self) -> Dict[str, Any]:
        """获取当前上下文"""
        if not hasattr(self, "_context"):
            self._context = {}
        return self._context

    def get_entries(self) -> List[ExecutionLogEntry]:
        """获取所有日志条目"""
        return self.entries

    def get_entries_by_level(self, level: str) -> List[ExecutionLogEntry]:
        """按级别获取日志条目"""
        return [e for e in self.entries if e.level == level]

    def get_entries_by_step(self, step_name: str) -> List[ExecutionLogEntry]:
        """按步骤获取日志条目"""
        return [e for e in self.entries if e.step_name == step_name]

    def get_errors(self) -> List[ExecutionLogEntry]:
        """获取所有错误日志"""
        return self.get_entries_by_level("error")

    def get_duration_ms(self) -> Optional[int]:
        """获取总执行时间（毫秒）"""
        if not self._start_time:
            return None
        entries = [e for e in self.entries if e.timestamp]
        if not entries:
            return None
        first = datetime.fromisoformat(entries[0].timestamp)
        last = datetime.fromisoformat(entries[-1].timestamp)
        return int((last - first).total_seconds() * 1000)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "entries": [e.to_dict() for e in self.entries],
            "entry_count": len(self.entries),
            "error_count": len(self.get_errors()),
            "duration_ms": self.get_duration_ms(),
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_to_file(self, filepath: str) -> None:
        """保存到文件"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    def summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "execution_id": self.execution_id,
            "entry_count": len(self.entries),
            "error_count": len(self.get_errors()),
            "duration_ms": self.get_duration_ms(),
            "entries_by_level": {
                level: len(self.get_entries_by_level(level))
                for level in ["debug", "info", "warning", "error"]
            },
        }


# ========== 全局执行日志管理器 ==========

class ExecutionLogManager:
    """执行日志管理器"""

    _instances: Dict[str, ExecutionLogger] = {}
    _default_execution_id: str = None

    @classmethod
    def get_logger(cls, execution_id: str = None) -> ExecutionLogger:
        """获取执行日志记录器"""
        if execution_id is None:
            if cls._default_execution_id is None:
                cls._default_execution_id = str(uuid.uuid4())
            execution_id = cls._default_execution_id

        if execution_id not in cls._instances:
            cls._instances[execution_id] = ExecutionLogger(execution_id)

        return cls._instances[execution_id]

    @classmethod
    def set_default(cls, execution_id: str) -> None:
        """设置默认执行 ID"""
        cls._default_execution_id = execution_id

    @classmethod
    def get_summary(cls, execution_id: str = None) -> Dict[str, Any]:
        """获取执行摘要"""
        logger = cls.get_logger(execution_id)
        return logger.summary()

    @classmethod
    def list_executions(cls) -> List[str]:
        """列出所有执行 ID"""
        return list(cls._instances.keys())


# ========== 便捷函数 ==========

def get_execution_logger(execution_id: str = None) -> ExecutionLogger:
    """获取执行日志记录器"""
    return ExecutionLogManager.get_logger(execution_id)


def log_execution(
    level: str,
    message: str,
    execution_id: str = None,
    **kwargs
) -> str:
    """便捷函数：记录执行日志"""
    logger = get_execution_logger(execution_id)
    return logger.log(level, message, **kwargs)


__all__ = [
    "ExecutionLogEntry",
    "ExecutionLogger",
    "ExecutionLogManager",
    "get_execution_logger",
    "log_execution",
]
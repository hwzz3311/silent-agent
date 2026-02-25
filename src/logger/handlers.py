"""
日志处理器模块

提供多种日志处理器。
"""

import gzip
import json
import logging
import sys
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict


class BaseHandler(ABC):
    """日志处理器基类"""

    @abstractmethod
    def emit(self, record: logging.LogRecord) -> None:
        """发送日志记录"""
        ...


class ConsoleHandler(BaseHandler):
    """控制台处理器"""

    def __init__(self, formatter: Callable = None, stream: str = "stdout"):
        self.formatter = formatter or logging.Formatter()
        self.stream = sys.stdout if stream == "stdout" else sys.stderr

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.formatter.format(record)
        self.stream.write(msg + "\n")
        self.stream.flush()


class FileHandler(BaseHandler):
    """文件处理器"""

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        encoding: str = "utf-8",
        formatter: Callable = None,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ):
        self.filename = Path(filename)
        self.mode = mode
        self.encoding = encoding
        self.formatter = formatter or logging.Formatter()
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._lock = threading.Lock()
        self._current_bytes = 0
        self._init_file()

    def _init_file(self) -> None:
        """初始化文件"""
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        if self.filename.exists():
            self._current_bytes = self.filename.stat().st_size

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.formatter.format(record)
        msg_bytes = (msg + "\n").encode(self.encoding)

        with self._lock:
            # 检查是否需要轮转
            if self._current_bytes + len(msg_bytes) > self.max_bytes:
                self._rotate()

            self._current_bytes += len(msg_bytes)

            with open(self.filename, self.mode, encoding=self.encoding) as f:
                f.write(msg + "\n")

    def _rotate(self) -> None:
        """日志轮转"""
        for i in range(self.backup_count - 1, 0, -1):
            src = self._get_backup_name(i)
            dst = self._get_backup_name(i + 1)
            if src.exists():
                src.rename(dst)

        # 压缩旧的日志文件
        if self._get_backup_name(1).exists():
            self._compress_backup(1)

        # 重命名当前文件
        if self.filename.exists():
            self._get_backup_name(1).rename(self.filename)

        self._current_bytes = 0

    def _get_backup_name(self, index: int) -> Path:
        """获取备份文件名"""
        if index == 0:
            return self.filename
        return self.filename.with_suffix(f".{index}.log.gz")

    def _compress_backup(self, index: int) -> None:
        """压缩备份文件"""
        src = self._get_backup_name(index)
        dst = self._get_backup_name(index)
        if src.exists():
            with open(src, 'rb') as f_in:
                with gzip.open(dst, 'wb') as f_out:
                    f_out.writelines(f_in)
            src.unlink()


class RotatingFileHandler(FileHandler):
    """轮转文件处理器（基于时间）"""

    def __init__(
        self,
        filename: str,
        when: str = "midnight",
        backup_count: int = 7,
        utc: bool = False,
        **kwargs,
    ):
        super().__init__(filename, **kwargs)
        self.when = when
        self.backup_count = backup_count
        self.utc = utc
        self._last_rotate_date = self._get_current_date()

    def _get_current_date(self) -> datetime:
        """获取当前日期"""
        now = datetime.utcnow() if self.utc else datetime.now()
        if self.when == "midnight":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.when == "hour":
            return now.replace(minute=0, second=0, microsecond=0)
        return now.date()

    def emit(self, record: logging.LogRecord) -> None:
        current_date = self._get_current_date()
        if current_date > self._last_rotate_date:
            with self._lock:
                if current_date > self._last_rotate_date:
                    self._rotate_by_date()
                    self._last_rotate_date = current_date

        super().emit(record)

    def _rotate_by_date(self) -> None:
        """按日期轮转"""
        # 压缩并重命名当前文件
        date_str = self._last_rotate_date.strftime("%Y%m%d")
        backup_name = self.filename.with_suffix(f".{date_str}.log.gz")

        if self.filename.exists():
            # 压缩当前文件
            with open(self.filename, 'rb') as f_in:
                with gzip.open(backup_name, 'wb') as f_out:
                    f_out.writelines(f_in)

            # 清空当前文件
            open(self.filename, 'w').close()
            self._current_bytes = 0

        # 删除过期的备份
        self._delete_old_backups()

    def _delete_old_backups(self) -> None:
        """删除过期备份"""
        keep = set()
        for i in range(1, self.backup_count + 1):
            keep.add(f".{i}.log.gz")

        for f in self.filename.parent.glob("*.log.gz"):
            if f.name not in keep:
                f.unlink()


class MemoryHandler(BaseHandler):
    """内存处理器（缓冲后批量处理）"""

    def __init__(
        self,
        buffer_size: int = 100,
        flush_on_level: int = logging.ERROR,
        target_handler: BaseHandler = None,
    ):
        self.buffer = []
        self.buffer_size = buffer_size
        self.flush_on_level = flush_on_level
        self.target_handler = target_handler
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        with self._lock:
            self.buffer.append(record)

            # 检查是否需要刷新
            if record.levelno >= self.flush_on_level or len(self.buffer) >= self.buffer_size:
                self.flush()

    def flush(self) -> None:
        """刷新缓冲区"""
        with self._lock:
            if not self.buffer:
                return

            if self.target_handler:
                for record in self.buffer:
                    self.target_handler.emit(record)

            self.buffer.clear()

    def close(self) -> None:
        """关闭处理器"""
        self.flush()


class WebSocketHandler(BaseHandler):
    """WebSocket 处理器"""

    def __init__(self, formatter: Callable = None):
        self.formatter = formatter or logging.Formatter()
        self.websocket = None
        self._lock = threading.Lock()

    def set_websocket(self, websocket) -> None:
        """设置 WebSocket 连接"""
        self.websocket = websocket

    def emit(self, record: logging.LogRecord) -> None:
        if not self.websocket:
            return

        msg = self.formatter.format(record)

        with self._lock:
            try:
                self.websocket.send(json.dumps({
                    "type": "log",
                    "data": msg,
                    "level": record.levelname,
                    "timestamp": datetime.utcnow().isoformat(),
                }))
            except Exception:
                pass


class ExecutionLoggerHandler(BaseHandler):
    """执行日志处理器（专用于 RPA 执行日志）"""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.entries = []
        self.start_time = None
        self.end_time = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """开始记录"""
        self.start_time = datetime.utcnow()

    def stop(self) -> None:
        """停止记录"""
        self.end_time = datetime.utcnow()

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "execution_id": self.execution_id,
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }

        # 添加步骤信息
        if hasattr(record, "step_name"):
            entry["step"] = record.step_name

        if hasattr(record, "tool_name"):
            entry["tool"] = record.tool_name

        if hasattr(record, "duration_ms"):
            entry["duration_ms"] = record.duration_ms

        if hasattr(record, "result"):
            entry["result"] = record.result

        # 添加异常信息
        if record.exc_info:
            entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        with self._lock:
            self.entries.append(entry)

    def get_entries(self) -> list:
        """获取所有日志条目"""
        return self.entries

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "execution_id": self.execution_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": (
                (self.end_time - self.start_time).total_seconds() * 1000
                if self.start_time and self.end_time else None
            ),
            "entries": self.entries,
            "entry_count": len(self.entries),
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_to_file(self, filepath: str) -> None:
        """保存到文件"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())


# ========== 处理器工厂 ==========

class HandlerFactory:
    """处理器工厂"""

    _handlers = {
        "console": ConsoleHandler,
        "file": FileHandler,
        "rotating_file": RotatingFileHandler,
        "memory": MemoryHandler,
        "websocket": WebSocketHandler,
        "execution": ExecutionLoggerHandler,
    }

    @classmethod
    def create(cls, handler_type: str, **kwargs) -> BaseHandler:
        """创建处理器"""
        handler_class = cls._handlers.get(handler_type)
        if not handler_class:
            raise ValueError(f"Unknown handler type: {handler_type}")
        return handler_class(**kwargs)


def create_handler(handler_type: str, **kwargs) -> BaseHandler:
    """便捷函数：创建处理器"""
    return HandlerFactory.create(handler_type, **kwargs)


__all__ = [
    "BaseHandler",
    "ConsoleHandler",
    "FileHandler",
    "RotatingFileHandler",
    "MemoryHandler",
    "WebSocketHandler",
    "ExecutionLoggerHandler",
    "HandlerFactory",
    "create_handler",
]
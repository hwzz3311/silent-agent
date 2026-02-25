"""
日志配置模块

提供日志系统的配置功能。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict


class LogLevel(Enum):
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormat(Enum):
    """日志格式"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass
class LogConfig:
    """日志配置"""
    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.STRUCTURED
    enable_console: bool = True
    enable_file: bool = True
    log_dir: str = field(default_factory=lambda: str(Path.home() / ".neurone" / "logs"))
    log_filename: str = field(default_factory=lambda: f"neurone_{datetime.now().strftime('%Y%m%d')}.log")
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    include_timestamp: bool = True
    include_level: bool = True
    include_logger_name: bool = True
    include_function: bool = False
    include_line_number: bool = True
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.name,
            "format": self.format.value,
            "enable_console": self.enable_console,
            "enable_file": self.enable_file,
            "log_dir": self.log_dir,
            "log_filename": self.log_filename,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
            "include_timestamp": self.include_timestamp,
            "include_level": self.include_level,
            "include_logger_name": self.include_logger_name,
            "include_function": self.include_function,
            "include_line_number": self.include_line_number,
            "extra_fields": self.extra_fields,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogConfig':
        return cls(
            level=LogLevel[data.get("level", "INFO")],
            format=LogFormat[data.get("format", "STRUCTURED")],
            enable_console=data.get("enable_console", True),
            enable_file=data.get("enable_file", True),
            log_dir=data.get("log_dir", str(Path.home() / ".neurone" / "logs")),
            log_filename=data.get("log_filename", f"neurone_{datetime.now().strftime('%Y%m%d')}.log"),
            max_bytes=data.get("max_bytes", 10 * 1024 * 1024),
            backup_count=data.get("backup_count", 5),
            include_timestamp=data.get("include_timestamp", True),
            include_level=data.get("include_level", True),
            include_logger_name=data.get("include_logger_name", True),
            include_function=data.get("include_function", False),
            include_line_number=data.get("include_line_number", True),
            extra_fields=data.get("extra_fields", {}),
        )

    @classmethod
    def default(cls) -> 'LogConfig':
        """获取默认配置"""
        return cls()

    @classmethod
    def development(cls) -> 'LogConfig':
        """开发环境配置"""
        return cls(
            level=LogLevel.DEBUG,
            format=LogFormat.DETAILED,
            enable_console=True,
            enable_file=False,
        )

    @classmethod
    def production(cls) -> 'LogConfig':
        """生产环境配置"""
        return cls(
            level=LogLevel.INFO,
            format=LogFormat.JSON,
            enable_console=False,
            enable_file=True,
            max_bytes=50 * 1024 * 1024,  # 50MB
            backup_count=10,
        )


class LoggerConfigManager:
    """日志配置管理器"""

    def __init__(self, config: LogConfig = None):
        self.config = config or LogConfig.default()
        self._config_cache = {}

    def get_config(self, logger_name: str = None) -> LogConfig:
        """获取配置"""
        if logger_name in self._config_cache:
            return self._config_cache[logger_name]

        # 创建继承的配置
        config = LogConfig.from_dict(self.config.to_dict())

        # 应用特定配置
        if logger_name:
            prefix = logger_name.split(".")[0]
            if prefix in self._config_cache:
                base_config = self._config_cache[prefix]
                config.level = base_config.level

        self._config_cache[logger_name] = config
        return config

    def set_level(self, level: LogLevel, logger_name: str = None) -> None:
        """设置日志级别"""
        self.config.level = level
        if logger_name:
            self._config_cache[logger_name] = LogConfig.from_dict(self.config.to_dict())

    def set_format(self, format: LogFormat) -> None:
        """设置日志格式"""
        self.config.format = format

    def set_log_file(self, log_dir: str, log_filename: str) -> None:
        """设置日志文件"""
        self.config.log_dir = log_dir
        self.config.log_filename = log_filename

    def ensure_log_dir(self) -> Path:
        """确保日志目录存在"""
        Path(self.config.log_dir).mkdir(parents=True, exist_ok=True)
        return Path(self.config.log_dir)

    def get_log_file_path(self) -> Path:
        """获取日志文件路径"""
        self.ensure_log_dir()
        return Path(self.config.log_dir) / self.config.log_filename


# 全局配置管理器
_config_manager = LoggerConfigManager()


def get_config_manager() -> LoggerConfigManager:
    """获取全局配置管理器"""
    return _config_manager


def configure_logger(
    logger_name: str = None,
    level: LogLevel = None,
    format: LogFormat = None,
    log_file: str = None,
) -> logging.Logger:
    """
    配置日志记录器

    Args:
        logger_name: 日志记录器名称
        level: 日志级别
        format: 日志格式
        log_file: 日志文件路径

    Returns:
        配置好的日志记录器
    """
    config = get_config_manager().get_config(logger_name)

    if level:
        config.level = level
    if format:
        config.format = format
    if log_file:
        config.log_filename = Path(log_file).name
        config.log_dir = str(Path(log_file).parent)

    return logging.getLogger(logger_name)


__all__ = [
    "LogLevel",
    "LogFormat",
    "LogConfig",
    "LoggerConfigManager",
    "get_config_manager",
    "configure_logger",
]
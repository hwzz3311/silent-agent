"""
配置模块

提供浏览器和应用的配置管理。
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from src.adapters.browser.factory import BrowserMode


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class BrowserSettings:
    """浏览器设置"""
    mode: BrowserMode = BrowserMode.HYBRID
    # Puppeteer 设置
    puppeteer_headless: bool = True
    puppeteer_args: List[str] = field(default_factory=list)
    puppeteer_executable_path: Optional[str] = None
    stealth_enabled: bool = True
    browser_ws_endpoint: Optional[str] = None
    # 扩展设置
    extension_path: Optional[str] = None
    # Relay 设置
    relay_host: str = "127.0.0.1"
    relay_port: int = 18792
    secret_key: Optional[str] = None
    # 连接设置
    connection_timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 1000
    # 运行时设置
    timeout: int = 30000  # 工具执行超时

    @classmethod
    def from_env(cls) -> "BrowserSettings":
        """从环境变量创建配置"""
        return cls(
            mode=BrowserMode(os.getenv("BROWSER_MODE", "hybrid")),
            puppeteer_headless=os.getenv("PUPPETEER_HEADLESS", "true").lower() == "true",
            puppeteer_args=os.getenv("PUPPETEER_ARGS", "").split(",") if os.getenv("PUPPETEER_ARGS") else [],
            puppeteer_executable_path=os.getenv("PUPPETEER_EXECUTABLE_PATH"),
            stealth_enabled=os.getenv("STEALTH_ENABLED", "true").lower() == "true",
            browser_ws_endpoint=os.getenv("BROWSER_WS_ENDPOINT"),
            extension_path=os.getenv("EXTENSION_PATH"),
            relay_host=os.getenv("RELAY_HOST", "127.0.0.1"),
            relay_port=int(os.getenv("RELAY_PORT", "18792")),
            secret_key=os.getenv("SECRET_KEY"),
        )


@dataclass
class RunnerConfig:
    """
    运行时配置 - 注入到工具执行

    用于在工具执行时传递运行时参数。
    可通过依赖注入方式获取，而非全局单例。
    """
    timeout: int = 30000  # 执行超时（毫秒）
    retry_count: int = 3  # 重试次数
    retry_delay: int = 1000  # 重试间隔（毫秒）
    browser_mode: str = "hybrid"  # 浏览器模式

    @classmethod
    def from_app_config(cls, config: "AppConfig") -> "RunnerConfig":
        """从应用配置创建运行时配置"""
        return cls(
            timeout=config.browser.timeout,
            retry_count=config.browser.retry_count,
            retry_delay=config.browser.retry_delay,
            browser_mode=config.browser.mode.value,
        )


@dataclass
class ServerSettings:
    """服务器设置"""
    host: str = "0.0.0.0"
    port: int = 8080
    reload: bool = False
    workers: int = 1
    # CORS
    cors_allow_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True


@dataclass
class LogSettings:
    """日志设置"""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s [%(levelname)s] %(message)s"
    date_format: str = "%H:%M:%S"
    file_path: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class AppConfig:
    """应用配置"""
    browser: BrowserSettings = field(default_factory=BrowserSettings)
    server: ServerSettings = field(default_factory=ServerSettings)
    log: LogSettings = field(default_factory=LogSettings)

    def create_runner_config(self) -> RunnerConfig:
        """创建运行时配置对象"""
        return RunnerConfig.from_app_config(self)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量加载配置"""
        # 浏览器配置
        browser = BrowserSettings(
            mode=BrowserMode(os.getenv("BROWSER_MODE", "hybrid")),
            puppeteer_headless=os.getenv("PUPPETEER_HEADLESS", "true").lower() == "true",
            puppeteer_args=os.getenv("PUPPETEER_ARGS", "").split(",") if os.getenv("PUPPETEER_ARGS") else [],
            puppeteer_executable_path=os.getenv("PUPPETEER_EXECUTABLE_PATH"),
            stealth_enabled=os.getenv("STEALTH_ENABLED", "true").lower() == "true",
            browser_ws_endpoint=os.getenv("BROWSER_WS_ENDPOINT"),
            extension_path=os.getenv("EXTENSION_PATH"),
            relay_host=os.getenv("RELAY_HOST", "127.0.0.1"),
            relay_port=int(os.getenv("RELAY_PORT", "18792")),
            secret_key=os.getenv("SECRET_KEY"),
        )

        # 服务器配置
        server = ServerSettings(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8080")),
            reload=os.getenv("SERVER_RELOAD", "false").lower() == "true",
            workers=int(os.getenv("SERVER_WORKERS", "1")),
        )

        # 日志配置
        log = LogSettings(
            level=LogLevel(os.getenv("LOG_LEVEL", "INFO")),
            file_path=os.getenv("LOG_FILE_PATH"),
        )

        return cls(browser=browser, server=server, log=log)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "browser": {
                "mode": self.browser.mode.value,
                "puppeteer": {
                    "headless": self.browser.puppeteer_headless,
                    "args": self.browser.puppeteer_args,
                    "executable_path": self.browser.puppeteer_executable_path,
                    "stealth_enabled": self.browser.stealth_enabled,
                },
                "extension": {
                    "path": self.browser.extension_path,
                },
                "relay": {
                    "host": self.browser.relay_host,
                    "port": self.browser.relay_port,
                },
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "reload": self.server.reload,
            },
            "log": {
                "level": self.log.level.value,
                "file_path": self.log.file_path,
            },
        }


# 配置实例（支持依赖注入）
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """获取配置（优先使用注入的配置，否则从环境创建）"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def set_config(config: AppConfig) -> None:
    """设置配置（用于测试注入 mock 配置）"""
    global _config
    _config = config


def reset_config() -> None:
    """重置配置（用于测试清理）"""
    global _config
    _config = None


__all__ = [
    "BrowserMode",
    "BrowserSettings",
    "ServerSettings",
    "LogSettings",
    "LogLevel",
    "RunnerConfig",
    "AppConfig",
    "get_config",
    "set_config",
    "reset_config",
]
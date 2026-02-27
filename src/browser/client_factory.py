"""
浏览器客户端工厂

提供多种浏览器客户端的创建和管理。
"""

import os
from enum import Enum
from typing import Optional, Dict, Any

from .base import BrowserClient, BrowserClientError


class BrowserMode(str, Enum):
    """浏览器客户端模式"""
    EXTENSION = "extension"  # 纯扩展模式（现有）
    PUPPETEER = "puppeteer"  # 纯 Puppeteer 模式
    HYBRID = "hybrid"  # 混合模式（Puppeteer + 扩展）


class BrowserConfig:
    """浏览器配置"""

    def __init__(
        self,
        mode: BrowserMode = BrowserMode.EXTENSION,
        # Puppeteer 配置
        puppeteer_headless: bool = True,
        puppeteer_args: list = None,
        puppeteer_executable_path: str = None,
        stealth_enabled: bool = True,
        # 扩展配置
        extension_path: str = None,
        relay_host: str = "127.0.0.1",
        relay_port: int = 18792,
        # 全局配置
        secret_key: str = None,
    ):
        self.mode = mode
        self.puppeteer_headless = puppeteer_headless
        self.puppeteer_args = puppeteer_args or []
        self.puppeteer_executable_path = puppeteer_executable_path
        self.stealth_enabled = stealth_enabled
        self.extension_path = extension_path
        self.relay_host = relay_host
        self.relay_port = relay_port
        self.secret_key = secret_key

    @classmethod
    def from_env(cls) -> "BrowserConfig":
        """从环境变量创建配置"""
        mode = BrowserMode(os.getenv("BROWSER_MODE", "extension"))

        puppeteer_args = os.getenv("PUPPETEER_ARGS", "").split(",") if os.getenv("PUPPETEER_ARGS") else []

        return cls(
            mode=mode,
            puppeteer_headless=os.getenv("PUPPETEER_HEADLESS", "true").lower() == "true",
            puppeteer_args=[a.strip() for a in puppeteer_args if a.strip()],
            puppeteer_executable_path=os.getenv("PUPPETEER_EXECUTABLE_PATH"),
            stealth_enabled=os.getenv("STEALTH_ENABLED", "true").lower() == "true",
            extension_path=os.getenv("EXTENSION_PATH"),
            relay_host=os.getenv("RELAY_HOST", "127.0.0.1"),
            relay_port=int(os.getenv("RELAY_PORT", "18792")),
            secret_key=os.getenv("SECRET_KEY"),
        )


class BrowserClientFactory:
    """
    浏览器客户端工厂

    根据配置创建对应的浏览器客户端。
    """

    _instance: Optional[BrowserClient] = None
    _config: Optional[BrowserConfig] = None

    @classmethod
    def set_config(cls, config: BrowserConfig) -> None:
        """设置配置（会重置客户端实例）"""
        cls._instance = None
        cls._config = config

    @classmethod
    def get_config(cls) -> BrowserConfig:
        """获取配置"""
        if cls._config is None:
            cls._config = BrowserConfig.from_env()
        return cls._config

    @classmethod
    def create_client(cls, mode: BrowserMode = None) -> BrowserClient:
        """
        创建浏览器客户端

        Args:
            mode: 客户端模式（可选，从配置读取）

        Returns:
            浏览器客户端实例
        """
        config = cls.get_config()
        mode = mode or config.mode

        if mode == BrowserMode.EXTENSION:
            from .extension_client import ExtensionClient
            return ExtensionClient(
                host=config.relay_host,
                port=config.relay_port,
                secret_key=config.secret_key,
            )
        elif mode == BrowserMode.PUPPETEER:
            from .puppeteer_client import PuppeteerClient
            return PuppeteerClient(
                headless=config.puppeteer_headless,
                args=config.puppeteer_args,
                stealth=config.stealth_enabled,
                executable_path=config.puppeteer_executable_path,
            )
        elif mode == BrowserMode.HYBRID:
            from .hybrid_client import HybridClient
            return HybridClient(
                puppeteer_config={
                    "headless": config.puppeteer_headless,
                    "args": config.puppeteer_args,
                    "stealth": config.stealth_enabled,
                    "executable_path": config.puppeteer_executable_path,
                },
                extension_config={
                    "host": config.relay_host,
                    "port": config.relay_port,
                    "secret_key": config.secret_key,
                },
            )
        else:
            raise BrowserClientError(f"Unknown browser mode: {mode}")

    @classmethod
    async def get_client(cls) -> BrowserClient:
        """
        获取单例客户端实例

        Returns:
            浏览器客户端实例
        """
        if cls._instance is None:
            cls._instance = cls.create_client()
            await cls._instance.connect()
        return cls._instance

    @classmethod
    async def close_client(cls) -> None:
        """关闭并重置客户端实例"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


# 便捷函数
def get_browser_client(mode: BrowserMode = None) -> BrowserClient:
    """获取浏览器客户端（便捷函数）"""
    return BrowserClientFactory.create_client(mode)


__all__ = [
    "BrowserMode",
    "BrowserConfig",
    "BrowserClientFactory",
    "get_browser_client",
]
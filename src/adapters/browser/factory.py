"""
浏览器客户端工厂

提供多种浏览器客户端的创建和管理。
"""

from typing import Optional

from src.ports.browser_port import BrowserPort
from src.config import BrowserMode, BrowserSettings


class BrowserClientError(Exception):
    """浏览器客户端错误"""
    pass

# 保持 BrowserConfig 别名以兼容旧代码
BrowserConfig = BrowserSettings


class BrowserClientFactory:
    """
    浏览器客户端工厂

    设计: 每次 create_client() 返回新实例，支持依赖注入
    """

    _config: Optional[BrowserConfig] = None

    @classmethod
    def set_config(cls, config: BrowserConfig) -> None:
        """设置配置"""
        cls._config = config

    @classmethod
    def get_config(cls) -> BrowserConfig:
        """获取配置"""
        if cls._config is None:
            cls._config = BrowserConfig.from_env()
        return cls._config

    @classmethod
    def create_client(cls, mode: BrowserMode = None) -> BrowserPort:
        """
        创建浏览器客户端（工厂方法，每次返回新实例）

        Args:
            mode: 客户端模式（可选从配置读取）

        Returns:
            浏览器客户端实例
        """
        config = cls.get_config()
        mode = mode or config.mode

        if mode == BrowserMode.EXTENSION:
            from .extension import ExtensionClient
            return ExtensionClient(
                host=config.relay_host,
                port=config.relay_port,
                secret_key=config.secret_key,
            )
        elif mode == BrowserMode.PUPPETEER:
            from .puppeteer import PuppeteerClient
            return PuppeteerClient(
                headless=config.puppeteer_headless,
                args=config.puppeteer_args,
                stealth=config.stealth_enabled,
                executable_path=config.puppeteer_executable_path,
                browser_ws_endpoint=config.browser_ws_endpoint,
            )
        elif mode == BrowserMode.HYBRID:
            from .hybrid import HybridClient
            return HybridClient(
                puppeteer_config={
                    "headless": config.puppeteer_headless,
                    "args": config.puppeteer_args,
                    "stealth": config.stealth_enabled,
                    "executable_path": config.puppeteer_executable_path,
                    "browser_ws_endpoint": config.browser_ws_endpoint,
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
    def create_client_for_instance(cls, instance: "BrowserInstance") -> BrowserPort:
        """
        根据浏览器实例创建客户端

        Args:
            instance: 浏览器实例

        Returns:
            浏览器客户端实例
        """
        mode = instance.mode

        if mode == BrowserMode.EXTENSION:
            from .extension import ExtensionClient
            return ExtensionClient(
                host=instance.relay_host,
                port=instance.relay_port,
                secret_key=instance.secret_key,
            )
        elif mode == BrowserMode.PUPPETEER:
            from .puppeteer import PuppeteerClient
            return PuppeteerClient(
                headless=True,
                args=[],
                stealth=True,
                browser_ws_endpoint=instance.ws_endpoint,
            )
        elif mode == BrowserMode.HYBRID:
            from .hybrid import HybridClient
            return HybridClient(
                puppeteer_config={
                    "headless": True,
                    "args": [],
                    "stealth": True,
                    "browser_ws_endpoint": instance.ws_endpoint,
                },
                extension_config={
                    "host": instance.relay_host,
                    "port": instance.relay_port,
                    "secret_key": instance.secret_key,
                },
            )
        else:
            raise BrowserClientError(f"Unknown browser mode: {mode}")


# 便捷函数
def get_browser_client(mode: BrowserMode = None) -> BrowserPort:
    """获取浏览器客户端（便捷函数）"""
    return BrowserClientFactory.create_client(mode)


__all__ = [
    "BrowserMode",
    "BrowserSettings",
    "BrowserConfig",
    "BrowserClientFactory",
    "get_browser_client",
]

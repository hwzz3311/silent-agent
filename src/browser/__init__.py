"""
浏览器模块

提供多种浏览器客户端实现：
- ExtensionClient: 通过 Chrome 扩展控制浏览器
- PuppeteerClient: 通过 Puppeteer 控制浏览器
- HybridClient: Puppeteer + 扩展混合模式
- UnifiedClient: 统一客户端接口
"""

from .client_factory import BrowserMode, BrowserClientFactory, get_browser_client
from .base import BrowserClient, BrowserClientError

__all__ = [
    "BrowserMode",
    "BrowserClientFactory",
    "get_browser_client",
    "BrowserClient",
    "BrowserClientError",
]
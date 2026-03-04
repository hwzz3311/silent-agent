"""
浏览器模块

提供多种浏览器客户端实现：
- ExtensionClient: 通过 Chrome 扩展控制浏览器
- PuppeteerClient: 通过 Puppeteer 控制浏览器
- HybridClient: Puppeteer + 扩展混合模式
- UnifiedClient: 统一客户端接口
- BrowserManager: 多实例管理器
- BrowserInstance: 浏览器实例数据类
"""

from .client_factory import BrowserMode, BrowserClientFactory, get_browser_client
from .base import BrowserClient, BrowserClientError
from .manager import BrowserManager
from .instance import BrowserInstance

__all__ = [
    "BrowserMode",
    "BrowserClientFactory",
    "get_browser_client",
    "BrowserClient",
    "BrowserClientError",
    "BrowserManager",
    "BrowserInstance",
]
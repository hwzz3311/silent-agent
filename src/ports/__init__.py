"""
端口层模块

定义浏览器操作的抽象端口，实现依赖倒置。
"""

from .browser_port import BrowserPort
from .browser_port_adapter import BrowserPortAdapter

__all__ = [
    "BrowserPort",
    "BrowserPortAdapter",
]

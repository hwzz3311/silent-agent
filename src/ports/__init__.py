"""
端口层模块

定义浏览器操作的抽象端口实现依赖倒置。
"""

from .browser_port import BrowserPort

__all__ = [
    "BrowserPort",
]

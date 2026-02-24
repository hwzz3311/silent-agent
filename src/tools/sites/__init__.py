"""
网站特定适配器模块

包含各种网站的 RPA 适配器实现。
"""

# 网站适配器
from .xiaohongshu import (
    XiaohongshuSite,
    XHSSiteConfig,
    XHSSelectors,
)

__all__ = [
    "XiaohongshuSite",
    "XHSSiteConfig",
    "XHSSelectors",
]
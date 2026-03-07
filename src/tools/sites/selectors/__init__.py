"""
选择器模块

所有网站共享的选择器定义。

目录结构:
- base.py    - 基类定义（BaseSelectorSet）
- common.py  - 实际使用的通用选择器（仅 search_input, search_button）
"""

from .base import (
    BaseSelectorSet,
)

from .common import (
    CommonSearchSelectors,
)


__all__ = [
    # Base
    "BaseSelectorSet",
    # Common
    "CommonSearchSelectors",
]

"""
选择器模块

提供通用的选择器基类和通用选择器定义。
各网站特定选择器继承这些基础类实现。
"""

from .base import (
    BasePageSelectors,
    BaseExtraSelectors,
    BaseSelectorSet,
)

from .common import (
    CommonPaginationSelectors,
    CommonModalSelectors,
    CommonSearchSelectors,
    CommonFeedSelectors,
    CommonDetailSelectors,
    CommonProfileSelectors,
    CommonPublishSelectors,
    CommonExtraSelectors,
    create_common_page_selectors,
)

__all__ = [
    # Base
    "BasePageSelectors",
    "BaseExtraSelectors",
    "BaseSelectorSet",
    # Common
    "CommonPaginationSelectors",
    "CommonModalSelectors",
    "CommonSearchSelectors",
    "CommonFeedSelectors",
    "CommonDetailSelectors",
    "CommonProfileSelectors",
    "CommonPublishSelectors",
    "CommonExtraSelectors",
    "create_common_page_selectors",
]

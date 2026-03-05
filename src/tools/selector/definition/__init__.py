"""
选择器定义模块

提供选择器基类和通用选择器定义。
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

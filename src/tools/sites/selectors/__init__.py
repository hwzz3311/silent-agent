"""
选择器模块

所有网站共享的选择器定义和运行时管理。

目录结构:
- base.py    - 基类定义（BasePageSelectors, BaseExtraSelectors, BaseSelectorSet）
- common.py  - 通用选择器（分页、弹窗、搜索、详情等）
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

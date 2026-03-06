"""
选择器模块

提供选择器定义和运行时管理功能。

目录结构:
- definition/  - 静态定义（基类、通用选择器）
- runtime/    - 运行时管理（版本管理、降级、验证）
"""

from .definition import (
    BasePageSelectors,
    BaseExtraSelectors,
    BaseSelectorSet,
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

from .runtime import (
    SelectorType,
    SelectorStatus,
    SelectorInfo,
    SelectorTestResult,
    SelectorManager,
    GlobalSelectorManager,
    get_selector_manager,
    set_selector_manager,
    reset_selector_manager,
)

__all__ = [
    # Definition - Base
    "BasePageSelectors",
    "BaseExtraSelectors",
    "BaseSelectorSet",
    # Definition - Common
    "CommonPaginationSelectors",
    "CommonModalSelectors",
    "CommonSearchSelectors",
    "CommonFeedSelectors",
    "CommonDetailSelectors",
    "CommonProfileSelectors",
    "CommonPublishSelectors",
    "CommonExtraSelectors",
    "create_common_page_selector",
    # Runtime
    "SelectorType",
    "SelectorStatus",
    "SelectorInfo",
    "SelectorTestResult",
    "SelectorManager",
    "GlobalSelectorManager",
    "get_selector_manager",
    "set_selector_manager",
    "reset_selector_manager",
]

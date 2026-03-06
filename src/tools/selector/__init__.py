"""
选择器模块

已迁移到 src/tools/sites/selectors/
此文件保留用于向后兼容请使用新导入路径 src.tools.sites.selectors
"""

# 重新导出保持向后兼容
from src.tools.sites.selectors import (
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
    SelectorType,
    SelectorInfo,
    SelectorTestResult,
    SelectorManager,
    GlobalSelectorManager,
    get_selector_manager,
    set_selector_manager,
    reset_selector_manager,
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
    # Manager
    "SelectorType",
    "SelectorInfo",
    "SelectorTestResult",
    "SelectorManager",
    "GlobalSelectorManager",
    "get_selector_manager",
    "set_selector_manager",
    "reset_selector_manager",
]

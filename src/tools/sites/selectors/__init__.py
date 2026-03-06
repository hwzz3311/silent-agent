"""
选择器模块

已迁移到 src/tools/selector/
此文件保留用于向后兼容，请使用新导入路径。
"""

# 重新导出保持向后兼容
from src.tools.selector.definition import (
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

from src.tools.selector.runtime import (
    SelectorType,
    SelectorStatus,
    SelectorInfo,
    SelectorTestResult,
    SelectorManager,
    GlobalSelectorManager,
    global_selector_manager,
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
    # Runtime
    "SelectorType",
    "SelectorStatus",
    "SelectorInfo",
    "SelectorTestResult",
    "SelectorManager",
    "GlobalSelectorManager",
    "global_selector_manager",
]

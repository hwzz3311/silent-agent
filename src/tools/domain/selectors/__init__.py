"""
选择器管理模块

已迁移到 src/tools/selector/runtime/
此文件保留用于向后兼容，请使用新导入路径。
"""

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
    "SelectorType",
    "SelectorStatus",
    "SelectorInfo",
    "SelectorTestResult",
    "SelectorManager",
    "GlobalSelectorManager",
    "global_selector_manager",
]

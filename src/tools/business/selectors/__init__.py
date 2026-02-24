"""
选择器管理模块

提供选择器版本管理、自动降级和验证功能。
"""

from .manager import (
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
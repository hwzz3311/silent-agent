"""
选择器运行时管理模块

提供选择器版本管理、自动降级和验证功能。
"""

from .manager import (
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

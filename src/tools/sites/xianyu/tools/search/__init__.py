"""
闲鱼搜索工具模块

提供商品搜索相关工具。
"""

from .search_item import SearchItemTool, search_item, XYSearchItemParams, XYSearchItemResult
from .types import XYSearchItem  # XYSearchItem 未在 search_item 中导出


def register():
    """工具已通过 @business_tool 装饰器自动注册"""
    return 0  # 装饰器自动注册，无需手动调用


__all__ = [
    "SearchItemTool",
    "search_item",
    "XYSearchItemParams",
    "XYSearchItem",
    "XYSearchItemResult",
    "register",
]

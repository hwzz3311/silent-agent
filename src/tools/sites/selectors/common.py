"""
通用选择器定义

保留实际使用的选择器（search_input, search_button）。
"""

from typing import List
from pydantic import BaseModel


class CommonSearchSelectors(BaseModel):
    """
    通用搜索选择器

    实际使用的选择器：search_input, search_button
    """
    search_input: str = ".search-input, [contenteditable='true'], [data-testid='search-input']"
    search_button: str = ".search-btn, .search-icon, [data-testid='search-btn']"


__all__ = [
    "CommonSearchSelectors",
]

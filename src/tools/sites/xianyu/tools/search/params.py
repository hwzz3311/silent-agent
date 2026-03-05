"""
闲鱼搜索商品工具参数

提供搜索商品相关工具的参数定义。
"""

from typing import Optional, List
from pydantic import Field

from src.tools.base import ToolParameters


class XYSearchItemParams(ToolParameters):
    """
    闲鱼搜索商品工具参数

    Attributes:
        tab_id: 可选的标签页 ID
        keyword: 搜索关键词
        pages: 获取页数（默认1）
        items_per_page: 每页商品数（默认30）
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )
    keyword: str = Field(
        ...,
        min_length=1,
        description="搜索关键词"
    )
    pages: int = Field(
        default=1,
        ge=1,
        le=10,
        description="获取页数，1-10页"
    )
    items_per_page: int = Field(
        default=30,
        ge=1,
        le=50,
        description="每页商品数"
    )


__all__ = [
    "XYSearchItemParams",
]

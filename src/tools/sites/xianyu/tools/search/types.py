"""
闲鱼搜索工具类型定义

提供搜索商品相关的参数和结果类型定义。
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from src.tools.base import ToolParameters
from src.tools.mixins import ToDictMixin


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
        description="标签页 ID默认使用当前活动标签页"
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


class XYSearchItem(BaseModel, ToDictMixin):
    """
    单个搜索商品信息
    """
    index: int = Field(default=0, description="序号")
    id: str = Field(default="", description="商品ID")
    title: str = Field(default="", description="商品标题")
    price: str = Field(default="", description="价格")
    wants: str = Field(default="0", description="想要人数")
    image: str = Field(default="", description="图片URL")
    seller: str = Field(default="", description="卖家地区")
    seller_credit: str = Field(default="", description="信誉标签")
    tags: List[str] = Field(default_factory=list, description="商品标签")
    url: str = Field(default="", description="商品链接")


class XYSearchItemResult(BaseModel, ToDictMixin):
    """
    闲鱼搜索商品结果

    Attributes:
        success: 是否成功
        keyword: 搜索关键词
        total_page: 获取的总页数
        total_items: 获取的商品总数
        results: 商品列表
        message: 结果描述信息
    """
    success: bool = False
    keyword: str = ""
    total_page: int = 0
    total_items: int = 0
    results: List[XYSearchItem] = Field(default_factory=list, description="商品列表")
    message: str = ""


__all__ = [
    "XYSearchItemParams",
    "XYSearchItem",
    "XYSearchItemResult",
]

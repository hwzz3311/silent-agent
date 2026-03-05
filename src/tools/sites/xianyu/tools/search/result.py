"""
闲鱼搜索商品工具结果

提供搜索商品相关工具的结果定义。
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class XYSearchItem(BaseModel):
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


class XYSearchItemResult(BaseModel):
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

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return self.model_dump() if hasattr(self, 'model_dump') else self.dict()


__all__ = [
    "XYSearchItem",
    "XYSearchItemResult",
]

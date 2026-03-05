"""
闲鱼发布商品工具参数

提供发布商品相关工具的参数定义。
"""

from typing import Optional, List
from pydantic import Field

from src.tools.base import ToolParameters


class XYPublishItemParams(ToolParameters):
    """
    闲鱼发布商品工具参数

    Attributes:
        tab_id: 可选的标签页 ID
        price: 商品价格
        description: 商品描述/正文
        images: 图片路径列表（本地路径）
        category_index: 分类索引（默认3=其他技能服务）
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )
    price: str = Field(
        ...,
        description="商品价格"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="商品描述，1-2000字符"
    )
    images: Optional[List[str]] = Field(
        default=None,
        description="图片路径列表（本地路径，支持1-9张）"
    )
    category_index: int = Field(
        default=3,
        description="分类索引（默认3=其他技能服务，0-9）"
    )


__all__ = [
    "XYPublishItemParams",
]

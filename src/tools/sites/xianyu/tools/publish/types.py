"""
闲鱼发布商品工具类型定义

提供发布商品相关的参数和结果定义。
"""

from typing import Optional, List
from pydantic import Field, BaseModel

from src.tools.base import ToolParameters
from src.tools.mixins import ToDictMixin


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


class XYPublishItemResult(BaseModel, ToDictMixin):
    """
    闲鱼发布商品结果

    Attributes:
        success: 操作是否成功
        item_id: 商品ID
        url: 商品链接
        message: 状态描述消息
    """
    success: bool = False
    item_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""


__all__ = [
    "XYPublishItemParams",
    "XYPublishItemResult",
]

"""
闲鱼发布商品工具结果

提供发布商品相关工具的结果定义。
"""

from typing import Optional
from pydantic import BaseModel


class XYPublishItemResult(BaseModel):
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
    "XYPublishItemResult",
]

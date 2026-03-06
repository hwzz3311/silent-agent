"""
小红书互动工具类型定义

提供互动相关工具的参数和结果定义。
"""

from typing import Optional, List
from pydantic import Field, BaseModel

from src.tools.base import ToolParameters
from src.tools.mixins import ToDictMixin


# ========== 参数定义 ==========

class XHSLikeFeedParams(ToolParameters):
    """
    小红书点赞工具参数

    Attributes:
        tab_id: 标签页 ID
        note_id: 笔记 ID
        action: 操作类型（like/unlike）
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    note_id: str = Field(
        ...,
        description="笔记 ID"
    )
    action: str = Field(
        default="like",
        description="操作类型: like/unlike"
    )


class XHSFavoriteFeedParams(ToolParameters):
    """
    小红书收藏工具参数

    Attributes:
        tab_id: 标签页 ID
        note_id: 笔记 ID
        action: 操作类型（favorite/unfavorite）
        folder_name: 文件夹名称（收藏时指定）
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    note_id: str = Field(
        ...,
        description="笔记 ID"
    )
    action: str = Field(
        default="favorite",
        description="操作类型: favorite/unfavorite"
    )
    folder_name: Optional[str] = Field(
        default=None,
        description="收藏文件夹名称"
    )


class XHSPostCommentParams(ToolParameters):
    """
    小红书发表评论工具参数

    Attributes:
        tab_id: 标签页 ID
        note_id: 笔记 ID
        content: 评论内容
        at_users: @用户列表
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    note_id: str = Field(
        ...,
        description="笔记 ID"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="评论内容，1-1000字符"
    )
    at_users: Optional[List[str]] = Field(
        default=None,
        description="@用户列表"
    )


class XHSReplyCommentParams(ToolParameters):
    """
    小红书回复评论工具参数

    Attributes:
        tab_id: 标签页 ID
        comment_id: 评论 ID
        content: 回复内容
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    comment_id: str = Field(
        ...,
        description="评论 ID"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="回复内容，1-1000字符"
    )


# ========== 结果定义 ==========

class XHSLikeFeedResult(BaseModel, ToDictMixin):
    """
    小红书点赞工具结果

    Attributes:
        success: 操作是否成功
        note_id: 笔记 ID
        action: 操作类型
        message: 状态描述消息
    """
    success: bool
    note_id: Optional[str] = None
    action: str = "like"
    message: str = ""


class XHSFavoriteFeedResult(BaseModel, ToDictMixin):
    """
    小红书收藏工具结果

    Attributes:
        success: 操作是否成功
        note_id: 笔记 ID
        action: 操作类型
        folder_name: 文件夹名称
        message: 状态描述消息
    """
    success: bool
    note_id: Optional[str] = None
    action: str = "favorite"
    folder_name: Optional[str] = None
    message: str = ""


class XHSPostCommentResult(BaseModel, ToDictMixin):
    """
    小红书发表评论工具结果

    Attributes:
        success: 操作是否成功
        comment_id: 评论 ID
        note_id: 笔记 ID
        content: 评论内容
        message: 状态描述消息
    """
    success: bool
    comment_id: Optional[str] = None
    note_id: Optional[str] = None
    content: Optional[str] = None
    message: str = ""


class XHSReplyCommentResult(BaseModel, ToDictMixin):
    """
    小红书回复评论工具结果

    Attributes:
        success: 操作是否成功
        reply_id: 回复 ID
        comment_id: 原评论 ID
        content: 回复内容
        message: 状态描述消息
    """
    success: bool
    reply_id: Optional[str] = None
    comment_id: Optional[str] = None
    content: Optional[str] = None
    message: str = ""


__all__ = [
    # 参数
    "XHSLikeFeedParams",
    "XHSFavoriteFeedParams",
    "XHSPostCommentParams",
    "XHSReplyCommentParams",
    # 结果
    "XHSLikeFeedResult",
    "XHSFavoriteFeedResult",
    "XHSPostCommentResult",
    "XHSReplyCommentResult",
]

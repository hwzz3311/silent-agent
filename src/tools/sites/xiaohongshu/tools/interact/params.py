"""
小红书互动工具参数

提供互动相关工具的参数定义。
"""

from typing import Optional, List
from pydantic import Field

from src.tools.base import ToolParameters


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


__all__ = [
    "XHSLikeFeedParams",
    "XHSFavoriteFeedParams",
    "XHSPostCommentParams",
    "XHSReplyCommentParams",
]
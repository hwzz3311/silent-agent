"""
小红书互动工具结果

提供互动相关工具的结果定义。
"""

from typing import Optional
from pydantic import BaseModel


class XHSLikeFeedResult(BaseModel):
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

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "note_id": self.note_id,
            "action": self.action,
            "message": self.message,
        }


class XHSFavoriteFeedResult(BaseModel):
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

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "note_id": self.note_id,
            "action": self.action,
            "folder_name": self.folder_name,
            "message": self.message,
        }


class XHSPostCommentResult(BaseModel):
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

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "comment_id": self.comment_id,
            "note_id": self.note_id,
            "content": self.content,
            "message": self.message,
        }


class XHSReplyCommentResult(BaseModel):
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

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "reply_id": self.reply_id,
            "comment_id": self.comment_id,
            "content": self.content,
            "message": self.message,
        }


__all__ = [
    "XHSLikeFeedResult",
    "XHSFavoriteFeedResult",
    "XHSPostCommentResult",
    "XHSReplyCommentResult",
]
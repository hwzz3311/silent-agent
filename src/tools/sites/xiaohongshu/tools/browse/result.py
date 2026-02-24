"""
小红书浏览工具结果

提供浏览相关工具的结果定义。
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class XHSFeedItem(BaseModel):
    """
    小红书笔记项

    Attributes:
        note_id: 笔记 ID
        title: 标题
        cover_image: 封面图片
        author: 作者信息
        likes: 点赞数
        comments: 评论数
        collects: 收藏数
        url: 笔记 URL
    """
    note_id: Optional[str] = None
    title: Optional[str] = None
    cover_image: Optional[str] = None
    author: Optional[Dict[str, Any]] = None
    likes: int = 0
    comments: int = 0
    collects: int = 0
    url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "note_id": self.note_id,
            "title": self.title,
            "cover_image": self.cover_image,
            "author": self.author,
            "likes": self.likes,
            "comments": self.comments,
            "collects": self.collects,
            "url": self.url,
        }


class XHSListFeedsResult(BaseModel):
    """
    小红书浏览笔记列表工具结果

    Attributes:
        success: 操作是否成功
        items: 笔记列表
        has_more: 是否有更多内容
        next_cursor: 下一页游标
        total_count: 总数量
        message: 状态描述消息
    """
    success: bool
    items: List[XHSFeedItem] = []
    has_more: bool = False
    next_cursor: Optional[str] = None
    total_count: int = 0
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "items": [item.to_dict() for item in self.items],
            "has_more": self.has_more,
            "next_cursor": self.next_cursor,
            "total_count": self.total_count,
            "message": self.message,
        }


class XHSSearchFeedsResult(BaseModel):
    """
    小红书搜索笔记工具结果

    Attributes:
        success: 操作是否成功
        items: 搜索结果列表
        search_type: 搜索类型
        keyword: 搜索关键词
        total_count: 总数量
        message: 状态描述消息
    """
    success: bool
    items: List[Dict[str, Any]] = []
    search_type: str = "notes"
    keyword: str = ""
    total_count: int = 0
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "items": self.items,
            "search_type": self.search_type,
            "keyword": self.keyword,
            "total_count": self.total_count,
            "message": self.message,
        }


class XHSGetFeedDetailResult(BaseModel):
    """
    小红书获取笔记详情工具结果

    Attributes:
        success: 操作是否成功
        note_id: 笔记 ID
        title: 标题
        content: 正文内容
        images: 图片列表
        author: 作者信息
        likes: 点赞数
        comments: 评论数
        collects: 收藏数
        comments_list: 评论列表
        publish_time: 发布时间
        url: 笔记 URL
        message: 状态描述消息
    """
    success: bool
    note_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    images: List[str] = []
    author: Optional[Dict[str, Any]] = None
    likes: int = 0
    comments: int = 0
    collects: int = 0
    comments_list: List[Dict[str, Any]] = []
    publish_time: Optional[str] = None
    url: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "note_id": self.note_id,
            "title": self.title,
            "content": self.content,
            "images": self.images,
            "author": self.author,
            "likes": self.likes,
            "comments": self.comments,
            "collects": self.collects,
            "comments_list": self.comments_list,
            "publish_time": self.publish_time,
            "url": self.url,
            "message": self.message,
        }


class XHSUserProfileResult(BaseModel):
    """
    小红书获取用户主页工具结果

    Attributes:
        success: 操作是否成功
        user_id: 用户 ID
        nickname: 昵称
        avatar: 头像 URL
        description: 个人简介
        followers: 粉丝数
        following: 关注数
        likes: 获赞数
        notes_count: 笔记数
        notes: 用户笔记列表
        message: 状态描述消息
    """
    success: bool
    user_id: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
    followers: int = 0
    following: int = 0
    likes: int = 0
    notes_count: int = 0
    notes: List[XHSFeedItem] = []
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "user_id": self.user_id,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "description": self.description,
            "followers": self.followers,
            "following": self.following,
            "likes": self.likes,
            "notes_count": self.notes_count,
            "notes": [note.to_dict() for note in self.notes],
            "message": self.message,
        }


__all__ = [
    "XHSFeedItem",
    "XHSListFeedsResult",
    "XHSSearchFeedsResult",
    "XHSGetFeedDetailResult",
    "XHSUserProfileResult",
]
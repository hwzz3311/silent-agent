"""
小红书浏览工具类型定义

提供浏览相关工具的参数和结果定义。
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from src.tools.base import ToolParameters
from src.tools.mixins import ToDictMixin


# ============== 参数定义 ==============

class XHSListFeedsParams(ToolParameters):
    """
    小红书浏览笔记列表工具参数

    Attributes:
        tab_id: 标签页 ID
        page_type: 页面类型（home/discover/following）
        channel: 频道类型，默认 recommend（推荐），可选值：recommend/fashion/food/cosmetics/movie_and_tv/career/love/household_product/gaming/travel/fitness
        max_items: 最大获取数量，默认 20
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    page_type: str = Field(
        default="home",
        description="页面类型: home/discover/following"
    )
    channel: str = Field(
        default="recommend",
        description="频道类型: recommend(推荐)/fashion(穿搭)/food(美食)/cosmetics(美妆)/movie_and_tv(影视)/career(职场)/love(情感)/household_product(家居)/gaming(游戏)/travel(旅行)/fitness(健身)"
    )
    max_items: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最大获取数量"
    )


class XHSSearchFeedsParams(ToolParameters):
    """
    小红书搜索笔记工具参数

    Attributes:
        tab_id: 标签页 ID
        keyword: 搜索关键词
        search_type: 搜索类型（notes/users/tags）
        max_items: 最大获取数量
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    keyword: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="搜索关键词"
    )
    search_type: str = Field(
        default="notes",
        description="搜索类型: notes/users/tags"
    )
    max_items: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最大获取数量"
    )


class XHSGetFeedDetailParams(ToolParameters):
    """
    小红书获取笔记详情工具参数

    Attributes:
        tab_id: 标签页 ID
        note_id: 笔记 ID
        include_comments: 是否包含评论，默认 True
        max_comments: 最大获取评论数量
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    note_id: str = Field(
        ...,
        description="笔记 ID"
    )
    include_comments: bool = Field(
        default=True,
        description="是否包含评论"
    )
    max_comments: int = Field(
        default=50,
        ge=1,
        le=200,
        description="最大获取评论数量"
    )


class XHSUserProfileParams(ToolParameters):
    """
    小红书获取用户主页工具参数

    Attributes:
        tab_id: 标签页 ID
        user_id: 用户 ID
        include_notes: 是否包含笔记列表，默认 True
        max_note: 最大获取笔记数量
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="用户 ID（可选，不提供则获取当前用户）"
    )
    include_notes: bool = Field(
        default=True,
        description="是否包含笔记列表"
    )
    max_note: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最大获取笔记数量"
    )


# ============== 结果定义 ==============

class XHSFeedItem(BaseModel, ToDictMixin):
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


class XHSListFeedsResult(BaseModel, ToDictMixin):
    """
    小红书浏览笔记列表工具结果

    Attributes:
        success: 操作是否成功
        item: 笔记列表
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


class XHSSearchFeedsResult(BaseModel, ToDictMixin):
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


class XHSGetFeedDetailResult(BaseModel, ToDictMixin):
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
    comment: int = 0
    collects: int = 0
    comments_list: List[Dict[str, Any]] = []
    publish_time: Optional[str] = None
    url: Optional[str] = None
    message: str = ""


class XHSUserProfileResult(BaseModel, ToDictMixin):
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


__all__ = [
    # 参数
    "XHSListFeedsParams",
    "XHSSearchFeedsParams",
    "XHSGetFeedDetailParams",
    "XHSUserProfileParams",
    # 结果
    "XHSFeedItem",
    "XHSListFeedsResult",
    "XHSSearchFeedsResult",
    "XHSGetFeedDetailResult",
    "XHSUserProfileResult",
]

"""
小红书浏览工具参数

提供浏览相关工具的参数定义。
"""

from typing import Optional, List
from pydantic import Field

from src.tools.base import ToolParameters


class XHSListFeedsParams(ToolParameters):
    """
    小红书浏览笔记列表工具参数

    Attributes:
        tab_id: 标签页 ID
        page_type: 页面类型（home/discover/following）
        max_items: 最大获取数量，默认 20
        scroll_count: 滚动次数，默认 3
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    page_type: str = Field(
        default="home",
        description="页面类型: home/discover/following"
    )
    max_items: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最大获取数量"
    )
    scroll_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="滚动次数"
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
        max_notes: 最大获取笔记数量
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
    max_notes: int = Field(
        default=20,
        ge=1,
        le=100,
        description="最大获取笔记数量"
    )


__all__ = [
    "XHSListFeedsParams",
    "XHSSearchFeedsParams",
    "XHSGetFeedDetailParams",
    "XHSUserProfileParams",
]
"""
小红书发布工具参数

提供发布相关工具的参数定义。
"""

from typing import Optional, List
from pydantic import Field

from src.tools.base import ToolParameters


class XHSPublishContentParams(ToolParameters):
    """
    小红书发布文本内容工具参数

    Attributes:
        tab_id: 标签页 ID
        title: 笔记标题
        content: 笔记正文内容
        images: 图片路径列表（本地路径或 URL）
        topic_tags: 话题标签列表
        at_users: @用户列表（用户 ID 或昵称）
        open_location: 位置信息（可选）
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="笔记标题，1-100字符"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="笔记正文内容，1-2000字符"
    )
    images: Optional[List[str]] = Field(
        default=None,
        description="图片路径列表（本地路径或 URL）"
    )
    topic_tags: Optional[List[str]] = Field(
        default=None,
        description="话题标签列表，如 ['#小红书', '#种草']"
    )
    at_users: Optional[List[str]] = Field(
        default=None,
        description="@用户列表，如 ['user1', 'user2']"
    )
    open_location: Optional[str] = Field(
        default=None,
        description="位置信息"
    )


class XHSPublishVideoParams(ToolParameters):
    """
    小红书发布视频内容工具参数

    Attributes:
        tab_id: 标签页 ID
        title: 笔记标题
        content: 笔记正文内容
        video_path: 视频文件路径（本地路径或 URL）
        cover_image: 封面图片路径（可选）
        topic_tags: 话题标签列表
        at_users: @用户列表
        open_location: 位置信息（可选）
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="笔记标题，1-100字符"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="笔记正文内容，1-2000字符"
    )
    video_path: str = Field(
        ...,
        description="视频文件路径（本地路径或 URL）"
    )
    cover_image: Optional[str] = Field(
        default=None,
        description="封面图片路径（可选）"
    )
    topic_tags: Optional[List[str]] = Field(
        default=None,
        description="话题标签列表，如 ['#小红书', '#视频']"
    )
    at_users: Optional[List[str]] = Field(
        default=None,
        description="@用户列表"
    )
    open_location: Optional[str] = Field(
        default=None,
        description="位置信息"
    )


class XHSSchedulePublishParams(ToolParameters):
    """
    小红书定时发布工具参数

    Attributes:
        tab_id: 标签页 ID
        title: 笔记标题
        content: 笔记正文内容
        images: 图片路径列表
        video_path: 视频文件路径（可选，与图片二选一）
        schedule_time: 定时发布时间（ISO 格式时间戳或日期时间字符串）
        timezone: 时区，默认 Asia/Shanghai
        topic_tags: 话题标签列表
        at_users: @用户列表
        open_location: 位置信息（可选）
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="笔记标题，1-100字符"
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="笔记正文内容，1-2000字符"
    )
    images: Optional[List[str]] = Field(
        default=None,
        description="图片路径列表（与 video_path 二选一）"
    )
    video_path: Optional[str] = Field(
        default=None,
        description="视频文件路径（与 images 二选一）"
    )
    schedule_time: str = Field(
        ...,
        description="定时发布时间（ISO 格式，如 2026-02-20T10:00:00）"
    )
    timezone: str = Field(
        default="Asia/Shanghai",
        description="时区"
    )
    topic_tags: Optional[List[str]] = Field(
        default=None,
        description="话题标签列表"
    )
    at_users: Optional[List[str]] = Field(
        default=None,
        description="@用户列表"
    )
    open_location: Optional[str] = Field(
        default=None,
        description="位置信息"
    )


class XHSCheckPublishStatusParams(ToolParameters):
    """
    小红书检查发布状态工具参数

    Attributes:
        tab_id: 标签页 ID
        note_id: 笔记 ID（可选，不提供则检查当前页面笔记）
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID"
    )
    note_id: Optional[str] = Field(
        default=None,
        description="笔记 ID（可选）"
    )


__all__ = [
    "XHSPublishContentParams",
    "XHSPublishVideoParams",
    "XHSSchedulePublishParams",
    "XHSCheckPublishStatusParams",
]
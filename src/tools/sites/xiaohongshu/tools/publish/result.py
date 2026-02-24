"""
小红书发布工具结果

提供发布相关工具的结果定义。
"""

from typing import Optional, List
from pydantic import BaseModel


class XHSPublishContentResult(BaseModel):
    """
    小红书发布文本内容工具结果

    Attributes:
        success: 操作是否成功
        note_id: 发布的笔记 ID
        url: 笔记访问 URL
        message: 状态描述消息
    """
    success: bool
    note_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "note_id": self.note_id,
            "url": self.url,
            "message": self.message,
        }


class XHSPublishVideoResult(BaseModel):
    """
    小红书发布视频内容工具结果

    Attributes:
        success: 操作是否成功
        note_id: 发布的笔记 ID
        url: 笔记访问 URL
        message: 状态描述消息
    """
    success: bool
    note_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "note_id": self.note_id,
            "url": self.url,
            "message": self.message,
        }


class XHSSchedulePublishResult(BaseModel):
    """
    小红书定时发布工具结果

    Attributes:
        success: 操作是否成功
        task_id: 定时任务 ID
        scheduled_time: 计划的发布时间
        message: 状态描述消息
    """
    success: bool
    task_id: Optional[str] = None
    scheduled_time: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "task_id": self.task_id,
            "scheduled_time": self.scheduled_time,
            "message": self.message,
        }


class XHSCheckPublishStatusResult(BaseModel):
    """
    小红书检查发布状态工具结果

    Attributes:
        success: 操作是否成功
        note_id: 笔记 ID
        status: 发布状态（draft/scheduled/published/failed）
        publish_time: 发布时间（如果已发布）
        views: 浏览量（如果已发布）
        likes: 点赞数（如果已发布）
        message: 状态描述消息
    """
    success: bool
    note_id: Optional[str] = None
    status: Optional[str] = None
    publish_time: Optional[str] = None
    views: int = 0
    likes: int = 0
    message: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "note_id": self.note_id,
            "status": self.status,
            "publish_time": self.publish_time,
            "views": self.views,
            "likes": self.likes,
            "message": self.message,
        }


__all__ = [
    "XHSPublishContentResult",
    "XHSPublishVideoResult",
    "XHSSchedulePublishResult",
    "XHSCheckPublishStatusResult",
]
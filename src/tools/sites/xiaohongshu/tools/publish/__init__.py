"""
小红书发布相关工具

包含图文发布、视频发布、定时发布等工具。
"""

from .publish_content import (
    PublishContentTool,
    publish_content,
    XHSPublishContentParams,
    XHSPublishContentResult,
)

from .publish_video import (
    PublishVideoTool,
    publish_video,
    XHSPublishVideoParams,
    XHSPublishVideoResult,
)

from .schedule_publish import (
    SchedulePublishTool,
    schedule_publish,
    XHSSchedulePublishParams,
    XHSSchedulePublishResult,
)

from .check_publish_status import (
    CheckPublishStatusTool,
    check_publish_status,
    XHSCheckPublishStatusParams,
    XHSCheckPublishStatusResult,
)


def register():
    """
    注册所有发布相关工具

    Returns:
        int: 注册的工具数量
    """
    from src.tools.business.registry import BusinessToolRegistry

    count = 0

    if BusinessToolRegistry.register_by_class(PublishContentTool):
        count += 1

    if BusinessToolRegistry.register_by_class(PublishVideoTool):
        count += 1

    if BusinessToolRegistry.register_by_class(SchedulePublishTool):
        count += 1

    if BusinessToolRegistry.register_by_class(CheckPublishStatusTool):
        count += 1

    return count


def get_tool_names() -> list:
    """获取所有发布工具名称"""
    return [
        "xhs_publish_content",
        "xhs_publish_video",
        "xhs_schedule_publish",
        "xhs_check_publish_status",
    ]


__all__ = [
    "register",
    "get_tool_names",
    "PublishContentTool",
    "publish_content",
    "PublishVideoTool",
    "publish_video",
    "SchedulePublishTool",
    "schedule_publish",
    "CheckPublishStatusTool",
    "check_publish_status",
]
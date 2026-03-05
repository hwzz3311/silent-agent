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
    """工具已通过 @business_tool 装饰器自动注册"""
    return 0  # 装饰器自动注册，无需手动调用


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
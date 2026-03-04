"""
闲鱼发布相关工具

包含商品发布等工具。
"""

from .publish_item import (
    PublishItemTool,
    publish_item,
    XYPublishItemParams,
    XYPublishItemResult,
)


def register():
    """
    注册所有发布相关工具

    Returns:
        int: 注册的工具数量
    """
    from src.tools.business.registry import BusinessToolRegistry

    count = 0

    if BusinessToolRegistry.register_by_class(PublishItemTool):
        count += 1

    return count


def get_tool_names() -> list:
    """获取所有发布工具名称"""
    return [
        "xianyu_publish_item",
    ]


__all__ = [
    "register",
    "get_tool_names",
    "PublishItemTool",
    "publish_item",
    "XYPublishItemParams",
    "XYPublishItemResult",
]

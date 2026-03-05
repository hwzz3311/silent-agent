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
    """工具已通过 @business_tool 装饰器自动注册"""
    return 0  # 装饰器自动注册，无需手动调用


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

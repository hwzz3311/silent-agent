"""
小红书登录检查工具参数

提供 xhs_check_login_status 工具的参数定义。
"""

from typing import Optional
from pydantic import Field

from src.tools.base import ToolParameters


class XHSCheckLoginStatusParams(ToolParameters):
    """
    小红书登录检查工具参数

    Attributes:
        tab_id: 可选的标签页 ID，默认使用当前活动标签页
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )


class XHSGetLoginQrcodeParams(ToolParameters):
    """
    小红书获取登录二维码工具参数

    Attributes:
        tab_id: 可选的标签页 ID，默认使用当前活动标签页
        auto_refresh: 是否自动刷新二维码，默认 True
        refresh_interval: 刷新间隔（秒），默认 60
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )
    auto_refresh: bool = Field(
        default=True,
        description="是否自动刷新二维码"
    )
    refresh_interval: int = Field(
        default=60,
        ge=30,
        le=300,
        description="刷新间隔（秒），30-300秒之间"
    )


class BHSDeleteCookiesParams(ToolParameters):
    """
    删除小红书 Cookie 工具参数

    Attributes:
        tab_id: 可选的标签页 ID，默认使用当前活动标签页
        delete_all: 是否删除所有 Cookie，默认 True
        cookie_names: 要删除的特定 Cookie 名称列表
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )
    delete_all: bool = Field(
        default=True,
        description="是否删除所有 Cookie"
    )
    cookie_names: Optional[list] = Field(
        default=None,
        description="要删除的特定 Cookie 名称列表"
    )


class XHSWaitLoginParams(ToolParameters):
    """
    小红书等待登录完成工具参数

    Attributes:
        tab_id: 可选的标签页 ID，默认使用当前活动标签页
        timeout: 超时时间（秒），默认 120
        check_interval: 检查间隔（秒），默认 2
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )
    timeout: int = Field(
        default=120,
        ge=30,
        le=600,
        description="超时时间（秒），30-600秒之间"
    )
    check_interval: int = Field(
        default=2,
        ge=1,
        le=10,
        description="检查间隔（秒），1-10秒之间"
    )


__all__ = [
    "XHSCheckLoginStatusParams",
    "XHSGetLoginQrcodeParams",
    "BHSDeleteCookiesParams",
    "XHSWaitLoginParams",
]
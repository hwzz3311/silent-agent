"""
小红书登录工具类型定义

提供登录相关工具的参数和结果类型定义。
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from src.tools.base import ToolParameters
from src.tools.mixins import ToDictMixin


# ==================== 参数类型 ====================

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


# ==================== 结果类型 ====================

class XHSCheckLoginStatusResult(BaseModel, ToDictMixin):
    """
    小红书登录检查工具结果

    Attributes:
        success: 操作是否成功
        is_logged_in: 是否已登录
        username: 用户名（已登录时返回）
        user_id: 用户 ID（已登录时返回）
        avatar: 头像 URL（已登录时返回）
        message: 状态描述消息
    """
    success: bool
    is_logged_in: bool = False
    username: Optional[str] = None
    user_id: Optional[str] = None
    avatar: Optional[str] = None
    message: str = ""


class XHSGetLoginQrcodeResult(BaseModel, ToDictMixin):
    """
    小红书获取登录二维码工具结果

    Attributes:
        success: 操作是否成功
        qrcode_url: 二维码图片 URL
        qrcode_data: 二维码原始数据（base64）
        expire_time: 过期时间戳
        message: 状态描述消息
    """
    success: bool
    qrcode_url: Optional[str] = None
    qrcode_data: Optional[str] = None
    expire_time: Optional[int] = None
    message: str = ""


class BHSDeleteCookiesResult(BaseModel, ToDictMixin):
    """
    删除小红书 Cookie 工具结果

    Attributes:
        success: 操作是否成功
        deleted_count: 删除的 Cookie 数量
        deleted_names: 删除的 Cookie 名称列表
        message: 状态描述消息
    """
    success: bool
    deleted_count: int = 0
    deleted_names: List[str] = []
    message: str = ""


class XHSWaitLoginResult(BaseModel, ToDictMixin):
    """
    小红书等待登录完成工具结果

    Attributes:
        success: 操作是否成功
        logged_in: 是否已登录
        username: 用户名（登录成功时返回）
        user_id: 用户 ID（登录成功时返回）
        avatar: 头像 URL（登录成功时返回）
        wait_time: 等待时间（秒）
        message: 状态描述消息
    """
    success: bool
    logged_in: bool = False
    username: Optional[str] = None
    user_id: Optional[str] = None
    avatar: Optional[str] = None
    wait_time: int = 0
    message: str = ""


# ==================== 导出列表 ====================

__all__ = [
    # 参数类型
    "XHSCheckLoginStatusParams",
    "XHSGetLoginQrcodeParams",
    "BHSDeleteCookiesParams",
    "XHSWaitLoginParams",
    # 结果类型
    "XHSCheckLoginStatusResult",
    "XHSGetLoginQrcodeResult",
    "BHSDeleteCookiesResult",
    "XHSWaitLoginResult",
]

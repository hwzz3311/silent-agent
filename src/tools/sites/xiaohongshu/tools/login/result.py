"""
小红书登录检查工具结果

提供 xhs_check_login_status 工具的结果定义。
"""

from typing import Optional, List
from pydantic import BaseModel


class XHSCheckLoginStatusResult(BaseModel):
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

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "is_logged_in": self.is_logged_in,
            "username": self.username,
            "user_id": self.user_id,
            "avatar": self.avatar,
            "message": self.message,
        }


class XHSGetLoginQrcodeResult(BaseModel):
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

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "qrcode_url": self.qrcode_url,
            "qrcode_data": self.qrcode_data,
            "expire_time": self.expire_time,
            "message": self.message,
        }


class BHSDeleteCookiesResult(BaseModel):
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

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "deleted_count": self.deleted_count,
            "deleted_names": self.deleted_names,
            "message": self.message,
        }


class XHSWaitLoginResult(BaseModel):
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

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "logged_in": self.logged_in,
            "username": self.username,
            "user_id": self.user_id,
            "avatar": self.avatar,
            "wait_time": self.wait_time,
            "message": self.message,
        }


__all__ = [
    "XHSCheckLoginStatusResult",
    "XHSGetLoginQrcodeResult",
    "BHSDeleteCookiesResult",
    "XHSWaitLoginResult",
]
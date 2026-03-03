"""
闲鱼密码登录工具结果

提供 xianyu_password_login 工具的结果定义。
"""

from typing import Optional, Dict
from pydantic import BaseModel


class PasswordLoginResult(BaseModel):
    """
    闲鱼密码登录工具结果

    Attributes:
        success: 操作是否成功
        cookies: 登录成功后的 Cookie 字典 {name: value}
        username: 用户名（登录成功时返回）
        user_id: 用户 ID（登录成功时返回）
        message: 状态描述消息
    """
    success: bool
    cookie: Optional[Dict[str, str]] = None
    username: Optional[str] = None
    user_id: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "cookie": self.cookie,
            "username": self.username,
            "user_id": self.user_id,
            "message": self.message,
        }


class GetCookiesResult(BaseModel):
    """
    闲鱼获取 Cookie 工具结果

    Attributes:
        success: 操作是否成功
        cookies: Cookie 字典 {name: value}
        is_logged_in: 是否已登录
        username: 用户名（已登录时返回）
        user_id: 用户 ID（已登录时返回）
        message: 状态描述消息
    """
    success: bool
    cookie: Optional[Dict[str, str]] = None
    is_logged_in: bool = False
    username: Optional[str] = None
    user_id: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "cookie": self.cookie,
            "is_logged_in": self.is_logged_in,
            "username": self.username,
            "user_id": self.user_id,
            "message": self.message,
        }


__all__ = [
    "PasswordLoginResult",
    "GetCookiesResult",
]

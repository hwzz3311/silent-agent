"""
闲鱼登录工具类型定义

提供 xianyu_password_login 和 xianyu_get_cookies 工具的参数和结果定义。
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field

from src.tools.base import ToolParameters
from src.tools.mixins import ToDictMixin


# ============== 参数定义 ==============

class PasswordLoginParams(ToolParameters):
    """
    闲鱼密码登录工具参数

    Attributes:
        account: 登录账号（手机号或邮箱）
        password: 登录密码
        headless: 是否使用无头模式，默认 True
    """
    account: str = Field(
        description="登录账号（手机号或邮箱）"
    )
    password: str = Field(
        description="登录密码"
    )
    headless: bool = Field(
        default=True,
        description="是否使用无头模式，默认 True"
    )


class GetCookiesParams(ToolParameters):
    """
    闲鱼获取 Cookie 工具参数

    使用已登录的浏览器会话，无需额外参数。

    Attributes:
        tab_id: 可选的标签页 ID默认使用当前活动标签页
        target_url: 可选的目标 URL，默认访问闲鱼首页
    """
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )
    target_url: Optional[str] = Field(
        default=None,
        description="目标 URL，默认访问 https://www.goofish.com"
    )


# ============== 结果定义 ==============

class PasswordLoginResult(BaseModel, ToDictMixin):
    """
    闲鱼密码登录工具结果

    Attributes:
        success: 操作是否成功
        cookie: 登录成功后的 Cookie 字典 {name: value}
        username: 用户名（登录成功时返回）
        user_id: 用户 ID（登录成功时返回）
        message: 状态描述消息
    """
    success: bool
    cookie: Optional[Dict[str, str]] = None
    username: Optional[str] = None
    user_id: Optional[str] = None
    message: str = ""


class GetCookieResult(BaseModel, ToDictMixin):
    """
    闲鱼获取 Cookie 工具结果

    Attributes:
        success: 操作是否成功
        cookie: Cookie 字典 {name: value}
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


__all__ = [
    # Params
    "PasswordLoginParams",
    "GetCookiesParams",
    # Result
    "PasswordLoginResult",
    "GetCookieResult",
]

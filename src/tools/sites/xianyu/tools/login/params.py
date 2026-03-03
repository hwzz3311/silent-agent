"""
闲鱼密码登录工具参数

提供 xianyu_password_login 工具的参数定义。
"""

from typing import Optional
from pydantic import Field

from src.tools.base import ToolParameters


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
        tab_id: 可选的标签页 ID，默认使用当前活动标签页
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


__all__ = [
    "PasswordLoginParams",
    "GetCookiesParams",
]

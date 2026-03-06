"""
闲鱼登录相关工具

提供登录状态检查、Cookie 获取等功能。
"""

import importlib
_get_cookies_module = importlib.import_module('.get_cookies', package=__name__)
from _get_cookies_module import (
    GetCookieTool,
    get_cookies,
    GetCookieParams,
    GetCookieResult,
)

from .types import (
    GetCookieParams,
    GetCookieResult,
    PasswordLoginParams,
    PasswordLoginResult,
)

from .password_login import PasswordLoginTool

__all__ = [
    # Get Cookie
    "GetCookieTool",
    "get_cookies",
    "GetCookieParams",
    "GetCookieResult",
    # Password Login
    "PasswordLoginParams",
    "PasswordLoginResult",
    "PasswordLoginTool",
]

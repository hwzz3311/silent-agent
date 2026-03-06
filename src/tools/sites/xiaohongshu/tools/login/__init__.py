"""
小红书登录相关工具

包含登录状态检查、获取二维码、删除Cookie、等待登录等工具。
"""

from .check_login_status import (
    CheckLoginStatusTool,
    check_login_status,
    XHSCheckLoginStatusParams,
    XHSCheckLoginStatusResult,
)

from .get_login_qrcode import (
    GetLoginQrcodeTool,
    get_login_qrcode,
    XHSGetLoginQrcodeParams,
    XHSGetLoginQrcodeResult,
)

from .delete_cookies import (
    DeleteCookiesTool,
    delete_cookies,
    BHSDeleteCookiesParams,
    BHSDeleteCookiesResult,
)

from .wait_login import (
    WaitLoginTool,
    wait_login,
    XHSWaitLoginParams,
    XHSWaitLoginResult,
)


def register():
    """工具已通过 @business_tool 装饰器自动注册"""
    return 0  # 装饰器自动注册，无需手动调用


__all__ = [
    "CheckLoginStatusTool",
    "check_login_status",
    "XHSCheckLoginStatusParams",
    "XHSCheckLoginStatusResult",
    "XHSGetLoginQrcodeParams",
    "XHSGetLoginQrcodeResult",
    "BHSDeleteCookiesParams",
    "BHSDeleteCookiesResult",
    "XHSWaitLoginParams",
    "XHSWaitLoginResult",
    "register",
    "get_tool_names",
]


def get_tool_names() -> list:
    """获取所有登录工具名称"""
    return [
        "xhs_check_login_status",
        "xhs_get_login_qrcode",
        "xhs_delete_cookies",
        "xhs_wait_login",
    ]
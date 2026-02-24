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
    """
    注册所有登录相关工具

    Returns:
        int: 注册的工具数量
    """
    from src.tools.business.registry import BusinessToolRegistry

    count = 0

    # 注册已实现的工具
    if BusinessToolRegistry.register_by_class(CheckLoginStatusTool):
        count += 1

    if BusinessToolRegistry.register_by_class(GetLoginQrcodeTool):
        count += 1

    if BusinessToolRegistry.register_by_class(DeleteCookiesTool):
        count += 1

    if BusinessToolRegistry.register_by_class(WaitLoginTool):
        count += 1

    return count


__all__ = [
    "CheckLoginStatusTool",
    "check_login_status",
    "XHSCheckLoginStatusParams",
    "XHSCheckLoginStatusResult",
    "register",
]


def get_tool_names() -> list:
    """获取所有登录工具名称"""
    return [
        "xhs_check_login_status",
        "xhs_get_login_qrcode",
        "xhs_delete_cookies",
        "xhs_wait_login",
    ]


__all__ = [
    "register",
    "get_tool_names",
]
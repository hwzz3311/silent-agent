"""
小红书等待登录完成工具

实现 xhs_wait_login 工具，等待用户扫描二维码完成登录。
"""

import time
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business import business_tool
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSWaitLoginParams
from .result import XHSWaitLoginResult


@business_tool(name="xhs_wait_login", site_type=XiaohongshuSite, operation_category="login")
class WaitLoginTool(BusinessTool[XiaohongshuSite, XHSWaitLoginParams]):
    """
    等待小红书登录完成

    轮询检查登录状态，直到用户成功登录或超时。

    Usage:
        tool = WaitLoginTool()
        result = await tool.execute(
            params=XHSWaitLoginParams(timeout=120),
            context=context
        )

        if result.success and result.data.logged_in:
            print(f"登录成功，用户: {result.data.username}")
    """

    name = "xhs_wait_login"
    description = "等待用户扫描二维码完成登录，轮询检查登录状态"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "login"
    required_login = False  # 此工具用于等待登录，不需要已登录

    # 直接模式类属性
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com"

    @log_operation("xhs_wait_login")
    async def _execute_core(
        self,
        params: XHSWaitLoginParams,
        context: ExecutionContext,
    ) -> Any:
        """
        核心执行逻辑

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            XHSWaitLoginResult: 等待结果
        """
        import logging

        logger = logging.getLogger(f"business_tool.{self.name}")

        # 使用 context.client（依赖注入）
        client = context.client
        if not client:
            return XHSWaitLoginResult(
                success=False,
                logged_in=False,
                message="无法获取浏览器客户端，请确保通过 API 调用"
            )

        # 使用 ensure_site_tab 获取标签页
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url=self.default_navigate_url,
            params_tab_id=params.tab_id
        )

        if not tab_id:
            return XHSWaitLoginResult(
                success=False,
                logged_in=False,
                message="无法获取标签页"
            )

        # 轮询检查登录状态
        start_time = time.time()
        timeout_seconds = params.timeout
        check_interval = params.check_interval

        # 辅助函数：通过 client 执行浏览器工具读取页面数据
        async def read_page_data(path: str):
            try:
                result = await client.execute_tool(
                    "read_page_data",
                    {"path": path, "tabId": tab_id},
                    timeout=10
                )
                if result.get("success"):
                    return result.get("data")
                return None
            except Exception as e:
                logger.debug(f"[wait_login] read_page_data 失败: {e}")
                return None

        while True:
            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                return XHSWaitLoginResult(
                    success=False,
                    logged_in=False,
                    wait_time=int(elapsed),
                    message=f"等待登录超时（{timeout_seconds}秒）"
                )

            # 检查登录状态（silent 模式减少轮询日志）
            try:
                # 方式1: 尝试读取全局变量中的用户信息
                data_sources = [
                    "__INITIAL_STATE__.user.userInfo",
                    "__NUXT__.data.0.userInfo",
                    "window.__USER_INFO__",
                    "window.__XHS_USER_INFO__",
                    "window.__xhs_user_info__",
                ]

                is_logged_in = False
                user_info = None

                for source in data_source:
                    data = await read_page_data(source)
                    if data:
                        # 检查是否有用户信息
                        if isinstance(data, dict):
                            if "isLogin" in data:
                                is_logged_in = data.get("isLogin", False)
                            elif "userInfo" in data:
                                user_info = data.get("userInfo", {})
                                is_logged_in = bool(user_info)

                        if is_logged_in:
                            logger.info(f"[wait_login] 通过 {source} 检测到登录状态")
                            break
                    if is_logged_in:
                        break

                # 方式2: 如果方式1未检测到，尝试读取 Cookie
                if not is_logged_in:
                    cookie_result = await client.execute_tool(
                        "browser_control",
                        {"action": "get_cookies", "params": {"domain": ".xiaohongshu.com"}},
                        timeout=10000
                    )
                    if cookie_result.get("success"):
                        cookies_list = cookie_result.get("data", {}).get("cookies", [])
                        # 检查常见登录 Cookie
                        login_cookies = ["a1", "webId", "web_build", "xsecappid"]
                        has_login_cookie = any(
                            any(c.get("name") == ck for ck in login_cookies)
                            for c in cookie_list
                        )
                        if has_login_cookie:
                            is_logged_in = True
                            logger.info("[wait_login] 通过 Cookie 检测到登录状态")

                # 方式3: 读取页面 DOM 中的登录状态指示器
                if not is_logged_in:
                    # 检查页面是否有用户头像元素（登录后会出现）
                    avatar_result = await client.execute_tool(
                        "read_page_data",
                        {"path": "document.querySelector('.user-avatar, [data-testid=user-avatar], .avatar')", "tabId": tab_id},
                        timeout=5000
                    )
                    if avatar_result.get("success") and avatar_result.get("data"):
                        is_logged_in = True
                        logger.info("[wait_login] 通过页面元素检测到登录状态")

                if is_logged_in:
                    # 登录成功
                    return XHSWaitLoginResult(
                        success=True,
                        logged_in=True,
                        username=user_info.get("nickname") if user_info else None,
                        user_id=user_info.get("userId") if user_info else None,
                        avatar=user_info.get("image") if user_info else None,
                        wait_time=int(elapsed),
                        message=f"登录成功，用户: {user_info.get('nickname', '未知') if user_info else '未知'}"
                    )

            except Exception as e:
                logger.debug(f"[wait_login] 检查登录状态失败: {e}")

            # 未登录继续等待
            await self._sleep(check_interval * 1000)

    async def _sleep(self, ms: int) -> None:
        """异步睡眠"""
        import asyncio
        await asyncio.sleep(ms / 1000)



# 便捷函数
async def wait_login(
    tab_id: int = None,
    timeout: int = 120,
    check_interval: int = 2,
    context: ExecutionContext = None
) -> XHSWaitLoginResult:
    """
    便捷的等待登录函数

    Args:
        tab_id: 标签页 ID
        timeout: 超时时间（秒）
        check_interval: 检查间隔（秒）
        context: 执行上下文

    Returns:
        XHSWaitLoginResult: 等待结果
    """
    tool = WaitLoginTool()
    params = XHSWaitLoginParams(
        tab_id=tab_id,
        timeout=timeout,
        check_interval=check_interval
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSWaitLoginResult(
            success=False,
            logged_in=False,
            message=f"等待登录失败: {result.error}"
        )


__all__ = [
    "WaitLoginTool",
    "wait_login",
    "XHSWaitLoginParams",
    "XHSWaitLoginResult",
]

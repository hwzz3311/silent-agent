"""
小红书等待登录完成工具

实现 xhs_wait_login 工具，等待用户扫描二维码完成登录。
"""

import time
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSWaitLoginParams
from .result import XHSWaitLoginResult


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
    site_type = XiaohongshuSite
    required_login = False  # 此工具用于等待登录，不需要已登录

    @log_operation("xhs_wait_login")
    async def _execute_core(
        self,
        params: XHSWaitLoginParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑

        Args:
            params: 工具参数
            context: 执行上下文
            site: 网站适配器实例

        Returns:
            XHSWaitLoginResult: 等待结果
        """
        start_time = time.time()
        timeout_seconds = params.timeout
        check_interval = params.check_interval

        # 轮询检查登录状态
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
            login_result = await site.check_login_status(context, silent=True)

            if not login_result.success:
                # 检查失败，短暂等待后重试
                await self._sleep(check_interval * 1000)
                continue

            login_data = login_result.data if isinstance(login_result.data, dict) else {}

            if login_data.get("is_logged_in", False):
                # 登录成功
                return XHSWaitLoginResult(
                    success=True,
                    logged_in=True,
                    username=login_data.get("username"),
                    user_id=login_data.get("user_id"),
                    avatar=login_data.get("avatar"),
                    wait_time=int(elapsed),
                    message=f"登录成功，用户: {login_data.get('username', '未知')}"
                )

            # 未登录，继续等待
            await self._sleep(check_interval * 1000)

    async def _sleep(self, ms: int) -> None:
        """异步睡眠"""
        import asyncio
        await asyncio.sleep(ms / 1000)

    def _get_status_message(self, is_logged_in: bool, username: str = None) -> str:
        """生成状态消息"""
        if is_logged_in:
            return f"登录成功，用户: {username or '未知'}"
        else:
            return "等待登录中..."

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


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
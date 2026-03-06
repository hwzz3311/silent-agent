"""
前置检查策略

提供工具执行前的前置检查接口和实现，用于验证登录状态、页面状态等。
"""

from abc import ABC, abstractmethod
from typing import Any

from src.core.result import Result, Error
from src.tools.domain.errors import BusinessErrorCode
from src.tools.base import ExecutionContext


class IPreCheck(ABC):
    """
    前置检查接口

    定义工具执行前的前置检查规范，用于验证登录状态、页面状态等。
    """

    @abstractmethod
    async def check(
        self,
        tool: Any,
        params: Any,
        context: ExecutionContext
    ) -> Result[bool]:
        """
        执行前置检查

        Args:
            tool: 待执行的工具对象
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[bool]: 检查结果，True 表示通过，False 表示未通过
        """
        pass


class DefaultPreCheck(IPreCheck):
    """
    默认前置检查

    空检查实现，直接返回成功。适用于不需要检查的工具。
    """

    async def check(
        self,
        tool: Any,
        params: Any,
        context: ExecutionContext
    ) -> Result[bool]:
        """
        执行前置检查

        直接返回成功结果，不做任何检查。

        Args:
            tool: 待执行的工具对象
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[bool]: 检查结果，直接返回成功
        """
        return Result.ok(True)


class LoginRequiredCheck(IPreCheck):
    """
    登录状态检查

    检查工具是否需要登录，如果需要则验证登录状态。
    """

    async def check(
        self,
        tool: Any,
        params: Any,
        context: ExecutionContext
    ) -> Result[bool]:
        """
        执行登录状态检查

        如果工具配置了 required_login=True，则：
        1. 获取工具对应的 Site 实例
        2. 调用 site.check_login_status 检查登录状态
        3. 如果未登录，返回失败结果（BusinessErrorCode.LOGIN_REQUIRED）

        Args:
            tool: 待执行的工具对象
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[bool]: 登录检查结果
        """
        # 检查工具是否需要登录
        required_login = getattr(tool, 'required_login', True)
        if not required_login:
            return Result.ok(True)

        # 获取 Site 实例
        site = self._get_site(tool, context)
        if site is None:
            # 无法获取 Site 实例，跳过检查（可能是通用工具）
            return Result.ok(True)

        # 检查登录状态
        try:
            login_result = await site.check_login_status(context, silent=True)
            if not login_result.success:
                # 检查登录状态失败，记录错误但继续执行
                return Result.ok(True)

            login_data = login_result.data or {}
            is_logged_in = login_data.get("is_logged_in", False)

            if not is_logged_in:
                return Result.fail(
                    error=Error(
                        code=BusinessErrorCode.LOGIN_REQUIRED.value,
                        message="需要登录后才能执行此操作",
                        details={"site": site.site_name, "tool": tool.name},
                        recoverable=True
                    )
                )

            return Result.ok(True)

        except Exception as e:
            # 检查过程中出现异常，跳过检查避免阻塞
            return Result.ok(True)

    def _get_site(self, tool: Any, context: ExecutionContext) -> Any:
        """
        获取 Site 实例

        Args:
            tool: 工具对象
            context: 执行上下文

        Returns:
            Site 实例，如果无法获取返回 None
        """
        site_type = getattr(tool, 'site_type', None)
        if site_type is None:
            return None

        try:
            # 创建 Site 实例
            site = site_type()

            # 更新超时配置
            if context and hasattr(site, 'config'):
                if hasattr(site.config, 'timeout'):
                    site.config.timeout = context.timeout
                if hasattr(site.config, 'retry_count'):
                    site.config.retry_count = context.retry_count

            return site
        except Exception:
            return None


__all__ = [
    "IPreCheck",
    "DefaultPreCheck",
    "LoginRequiredCheck",
]

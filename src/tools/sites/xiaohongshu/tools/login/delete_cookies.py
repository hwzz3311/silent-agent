"""
小红书删除 Cookie 工具

实现 xhs_delete_cookies 工具，删除小红书登录相关的 Cookie。
"""

from typing import Any, List

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.errors import BusinessException, BusinessErrorCode
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import BHSDeleteCookiesParams
from .result import BHSDeleteCookiesResult


class DeleteCookiesTool(BusinessTool[XiaohongshuSite, BHSDeleteCookiesParams]):
    """
    删除小红书登录 Cookie

    用于退出登录或清除登录状态。支持删除所有 Cookie 或特定 Cookie。

    Usage:
        tool = DeleteCookiesTool()
        result = await tool.execute(
            params=BHSDeleteCookiesParams(),
            context=context
        )

        if result.success:
            print(f"删除了 {result.data.deleted_count} 个 Cookie")
    """

    name = "xhs_delete_cookies"
    description = "删除小红书登录 Cookie，支持删除全部或指定 Cookie"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "login"
    site_type = XiaohongshuSite
    required_login = False  # 删除 Cookie 不需要已登录

    @log_operation("xhs_delete_cookies")
    async def _execute_core(
        self,
        params: BHSDeleteCookiesParams,
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
            BHSDeleteCookiesResult: 删除结果
        """
        # 调用网站适配器的删除 Cookie 方法
        delete_result = await site.delete_cookies(
            context,
            delete_all=params.delete_all,
            cookie_names=params.cookie_names
        )

        if not delete_result.success:
            return BHSDeleteCookiesResult(
                success=False,
                message=f"删除 Cookie 失败: {delete_result.error}"
            )

        # 解析删除结果
        result_data = delete_result.data if isinstance(delete_result.data, dict) else {}

        return BHSDeleteCookiesResult(
            success=True,
            deleted_count=result_data.get("deleted_count", 0),
            deleted_names=result_data.get("deleted_names", []),
            message=self._get_delete_message(result_data)
        )

    def _get_delete_message(self, result_data: dict) -> str:
        """生成删除结果消息"""
        deleted_count = result_data.get("deleted_count", 0)
        deleted_names = result_data.get("deleted_names", [])

        if deleted_count > 0:
            if len(deleted_names) > 5:
                names_preview = deleted_names[:5] + ["..."]
                return f"成功删除 {deleted_count} 个 Cookie: {', '.join(names_preview)}"
            elif deleted_names:
                return f"成功删除 {deleted_count} 个 Cookie: {', '.join(deleted_names)}"
            else:
                return f"成功删除 {deleted_count} 个 Cookie"
        else:
            return "未删除任何 Cookie"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def delete_cookies(
    tab_id: int = None,
    delete_all: bool = True,
    cookie_names: List[str] = None,
    context: ExecutionContext = None
) -> BHSDeleteCookiesResult:
    """
    便捷的删除 Cookie 函数

    Args:
        tab_id: 标签页 ID
        delete_all: 是否删除所有 Cookie
        cookie_names: 要删除的特定 Cookie 名称列表
        context: 执行上下文

    Returns:
        BHSDeleteCookiesResult: 删除结果
    """
    tool = DeleteCookiesTool()
    params = BHSDeleteCookiesParams(
        tab_id=tab_id,
        delete_all=delete_all,
        cookie_names=cookie_names
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return BHSDeleteCookiesResult(
            success=False,
            message=f"删除失败: {result.error}"
        )


__all__ = [
    "DeleteCookiesTool",
    "delete_cookies",
    "BHSDeleteCookiesParams",
    "BHSDeleteCookiesResult",
]
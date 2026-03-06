"""
小红书搜索笔记工具

实现 xhs_search_feeds 工具，搜索小红书内容。
"""

import logging
import asyncio
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.domain import business_tool
from src.tools.domain.base import BusinessTool
from src.tools.domain.logging import log_operation
from src.tools.domain.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSSearchFeedsParams
from .result import XHSSearchFeedsResult

# 创建日志记录器
logger = logging.getLogger("xhs_search_feeds")


@business_tool(name="xhs_search_feeds", site_type=XiaohongshuSite, param_type=XHSSearchFeedsParams, operation_category="browse")
class SearchFeedsTool(BusinessTool):
    """
    搜索小红书内容

    支持搜索笔记、用户、话题。

    Usage:
        tool = SearchFeedsTool()
        result = await tool.execute(
            params=XHSSearchFeedsParams(
                keyword="美妆教程",
                search_type="notes",
                max_items=20
            ),
            context=context
        )

        if result.success:
            for item in result.data.items:
                print(f"{item.get('title')}: {item.get('likes')} 点赞")
    """

    name = "xhs_search_feeds"
    description = "搜索小红书内容，支持笔记、用户、话题搜索"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "browse"
    required_login = False

    # 直接模式类属性
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/search/"

    @log_operation("xhs_search_feeds")
    async def _execute_core(
        self,
        params: XHSSearchFeedsParams,
        context: ExecutionContext,
    ) -> Any:
        """
        核心执行逻辑 - 直接模式

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）

        Returns:
            XHSSearchFeedsResult: 搜索结果
        """
        # 使用 context.client（依赖注入）
        client = context.client
        if not client:
            return XHSSearchFeedsResult(
                success=False,
                keyword=params.keyword,
                search_type=params.search_type,
                message="无法获取浏览器客户端请确保通过 API 调用"
            )

        # ========== 使用 ensure_site_tab 获取标签页 ==========
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url=self.default_navigate_url,
            param_tab_id=params.tab_id
        )

        if not tab_id:
            logger.error("无法获取或创建标签页，浏览器可能未打开")
            return XHSSearchFeedsResult(
                success=False,
                keyword=params.keyword,
                search_type=params.search_type,
                message="无法获取或创建标签页请确保浏览器已打开"
            )

        logger.debug(f"最终使用的 tab_id: {tab_id}")

        # ========== 执行搜索操作 ==========
        search_result = await self._search_direct(
            client=client,
            tab_id=tab_id,
            keyword=params.keyword,
            search_type=params.search_type,
            max_items=params.max_items
        )

        if not search_result.get("success"):
            return XHSSearchFeedsResult(
                success=False,
                keyword=params.keyword,
                search_type=params.search_type,
                message=f"搜索失败: {search_result.get('error', '未知错误')}"
            )

        # 解析搜索结果
        items_data = search_result.get("data", {}).get("items", []) or []

        return XHSSearchFeedsResult(
            success=True,
            items=items_data,
            search_type=params.search_type,
            keyword=params.keyword,
            total_count=len(items_data),
            message=self._get_search_message(params.keyword, items_data)
        )

    async def _search_direct(
        self,
        client,
        tab_id: int,
        keyword: str,
        search_type: str = "notes",
        max_items: int = 20
    ) -> dict:
        """直接执行搜索操作"""
        from src.tools.primitives.control import ControlTool

        try:
            # 导航到搜索页面
            await client.navigate(
                url=f"https://www.xiaohongshu.com/search_result?keyword={keyword}&type={search_type}",
                tab_id=tab_id
            )

            # 等待页面加载
            await asyncio.sleep(2)

            # 使用 ControlTool 执行搜索
            control_tool = ControlTool()
            params_type = control_tool._get_params_type()

            result = await control_tool.execute(
                params=params_type(
                    action="search",
                    keyword=keyword,
                    search_type=search_type,
                    max_items=max_items,
                    tab_id=tab_id
                ),
                context=ExecutionContext(client=client, timeout=30000)
            )

            if result.success:
                return {
                    "success": True,
                    "data": result.data if isinstance(result.data, dict) else {}
                }
            else:
                return {
                    "success": False,
                    "error": result.error or "搜索失败"
                }

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_search_message(self, keyword: str, items: list) -> str:
        """生成搜索消息"""
        count = len(items)
        if count == 0:
            return f"未找到与 '{keyword}' 相关的内容"
        elif count == 1:
            return f"找到 1 条与 '{keyword}' 相关的内容"
        else:
            return f"找到 {count} 条与 '{keyword}' 相关的内容"



# 便捷函数
async def search_feeds(
    keyword: str,
    search_type: str = "notes",
    max_items: int = 20,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSSearchFeedsResult:
    """
    便捷的搜索函数

    Args:
        keyword: 搜索关键词
        search_type: 搜索类型
        max_items: 最大获取数量
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSSearchFeedsResult: 搜索结果
    """
    tool = SearchFeedsTool()
    params = XHSSearchFeedsParams(
        tab_id=tab_id,
        keyword=keyword,
        search_type=search_type,
        max_items=max_items
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSSearchFeedsResult(
            success=False,
            keyword=keyword,
            search_type=search_type,
            message=f"搜索失败: {result.error}"
        )


__all__ = [
    "SearchFeedsTool",
    "search_feeds",
    "XHSSearchFeedsParams",
    "XHSSearchFeedsResult",
]
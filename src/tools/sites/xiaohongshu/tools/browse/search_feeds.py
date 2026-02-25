"""
小红书搜索笔记工具

实现 xhs_search_feeds 工具，搜索小红书内容。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSSearchFeedsParams
from .result import XHSSearchFeedsResult


class SearchFeedsTool(BusinessTool[XiaohongshuSite, XHSSearchFeedsParams]):
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
    site_type = XiaohongshuSite
    required_login = False

    @log_operation("xhs_search_feeds")
    async def _execute_core(
        self,
        params: XHSSearchFeedsParams,
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
            XHSSearchFeedsResult: 搜索结果
        """
        # 调用网站适配器的搜索方法
        search_result = await site.search(
            context,
            keyword=params.keyword,
            search_type=params.search_type,
            max_items=params.max_items
        )

        if not search_result.success:
            return XHSSearchFeedsResult(
                success=False,
                keyword=params.keyword,
                search_type=params.search_type,
                message=f"搜索失败: {search_result.error}"
            )

        # 解析搜索结果
        items_data = search_result.data or []

        return XHSSearchFeedsResult(
            success=True,
            items=items_data,
            search_type=params.search_type,
            keyword=params.keyword,
            total_count=len(items_data),
            message=self._get_search_message(params.keyword, items_data)
        )

    def _get_search_message(self, keyword: str, items: list) -> str:
        """生成搜索消息"""
        count = len(items)
        if count == 0:
            return f"未找到与 '{keyword}' 相关的内容"
        elif count == 1:
            return f"找到 1 条与 '{keyword}' 相关的内容"
        else:
            return f"找到 {count} 条与 '{keyword}' 相关的内容"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


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
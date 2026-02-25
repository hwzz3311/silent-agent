"""
小红书获取笔记详情工具

实现 xhs_get_feed_detail 工具，获取笔记详细信息。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSGetFeedDetailParams
from .result import XHSGetFeedDetailResult


class GetFeedDetailTool(BusinessTool[XiaohongshuSite, XHSGetFeedDetailParams]):
    """
    获取小红书笔记详情

    包括笔记内容、作者信息、点赞数、评论等详细信息。

    Usage:
        tool = GetFeedDetailTool()
        result = await tool.execute(
            params=XHSGetFeedDetailParams(note_id="abc123"),
            context=context
        )

        if result.success:
            print(f"标题: {result.data.title}")
            print(f"内容: {result.data.content}")
            print(f"点赞: {result.data.likes}")
    """

    name = "xhs_get_feed_detail"
    description = "获取小红书笔记详情，包括内容、作者、点赞、评论等信息"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "browse"
    site_type = XiaohongshuSite
    required_login = False

    @log_operation("xhs_get_feed_detail")
    async def _execute_core(
        self,
        params: XHSGetFeedDetailParams,
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
            XHSGetFeedDetailResult: 详情结果
        """
        # 调用网站适配器的提取数据方法
        extract_result = await site.extract_data(
            context=context,
            data_type="feed_detail",
            max_items=params.max_comments if params.include_comments else 0
        )

        if not extract_result.success:
            return XHSGetFeedDetailResult(
                success=False,
                note_id=params.note_id,
                message=f"获取笔记详情失败: {extract_result.error}"
            )

        # 解析详情结果
        detail_data = extract_result.data if isinstance(extract_result.data, dict) else {}

        return XHSGetFeedDetailResult(
            success=True,
            note_id=params.note_id or detail_data.get("note_id"),
            title=detail_data.get("title"),
            content=detail_data.get("content"),
            images=detail_data.get("images", []),
            author=detail_data.get("author"),
            likes=detail_data.get("likes", 0),
            comments=detail_data.get("comments", 0),
            collects=detail_data.get("collects", 0),
            comments_list=detail_data.get("comments_list", []) if params.include_comments else [],
            publish_time=detail_data.get("publish_time"),
            url=detail_data.get("url"),
            message=self._get_detail_message(detail_data)
        )

    def _get_detail_message(self, detail_data: dict) -> str:
        """生成详情消息"""
        title = detail_data.get("title")
        if title:
            return f"获取笔记详情成功: {title[:20]}..."
        return "获取笔记详情成功"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def get_feed_detail(
    note_id: str,
    include_comments: bool = True,
    max_comments: int = 50,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSGetFeedDetailResult:
    """
    便捷的获取笔记详情函数

    Args:
        note_id: 笔记 ID
        include_comments: 是否包含评论
        max_comments: 最大获取评论数量
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSGetFeedDetailResult: 详情结果
    """
    tool = GetFeedDetailTool()
    params = XHSGetFeedDetailParams(
        tab_id=tab_id,
        note_id=note_id,
        include_comments=include_comments,
        max_comments=max_comments
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSGetFeedDetailResult(
            success=False,
            note_id=note_id,
            message=f"获取失败: {result.error}"
        )


__all__ = [
    "GetFeedDetailTool",
    "get_feed_detail",
    "XHSGetFeedDetailParams",
    "XHSGetFeedDetailResult",
]
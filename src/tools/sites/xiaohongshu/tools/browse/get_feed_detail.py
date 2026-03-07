"""
小红书获取笔记详情工具

实现 xhs_get_feed_detail 工具，获取笔记详细信息。

直接模式：使用 context.client 直接执行浏览器操作
"""

import logging
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.domain import business_tool
from src.tools.domain.base import BusinessTool
from src.tools.domain.logging import log_operation
from src.tools.domain.site_base import Site
from src.tools.domain.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from src.tools.sites.xiaohongshu.utils.page_data import ReadPageDataTool
from .types import XHSGetFeedDetailParams, XHSGetFeedDetailResult

# 创建日志记录器
logger = logging.getLogger("xhs_get_feed_detail")


@business_tool(name="xhs_get_feed_detail", site_type=XiaohongshuSite, param_type=XHSGetFeedDetailParams, operation_category="browse")
class GetFeedDetailTool(BusinessTool):
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

    # 使用基类的 tab 管理抽象
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com"

    @log_operation("xhs_get_feed_detail")
    async def _execute_core(
        self,
        params: XHSGetFeedDetailParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑 - 直接模式

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）
            site: 网站适配器实例

        Returns:
            XHSGetFeedDetailResult: 详情结果
        """
        # 使用 context.client（依赖注入）
        client = context.client
        if not client:
            return XHSGetFeedDetailResult(
                success=False,
                note_id=params.note_id,
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
            return XHSGetFeedDetailResult(
                success=False,
                note_id=params.note_id,
                message="无法获取或创建标签页请确保浏览器已打开"
            )

        logger.debug(f"最终使用的 tab_id: {tab_id}")

        # ========== 直接从页面提取笔记详情 ==========
        detail_data = await self._extract_feed_detail_direct(client, tab_id)

        if not detail_data:
            return XHSGetFeedDetailResult(
                success=False,
                note_id=params.note_id,
                message="无法提取笔记详情数据请检查页面是否正确加载"
            )

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

    async def _extract_feed_detail_direct(self, client, tab_id: int) -> dict:
        """直接从页面提取笔记详情数据"""
        # 读取笔记详情数据
        sources = [
            "__INITIAL_STATE__.note.detailNote",
            "__NUXT__.data.0.note",
            "window.__NOTE_DETAIL__",
        ]

        detail_data = None
        for source in sources:
            try:
                result = await client.execute_tool("read_page_data", {
                    "path": source,
                    "tabId": tab_id
                }, timeout=15000)

                if result.get("success") and result.get("data"):
                    detail_data = result.get("data")
                    logger.debug(f"从 {source} 获取到笔记详情")
                    break
            except Exception as e:
                logger.debug(f"从 {source} 获取失败: {e}")
                continue

        if not detail_data:
            logger.warning("未能从全局变量获取笔记详情数据")
            return None

        # 解析详情数据
        return {
            "note_id": detail_data.get("noteId"),
            "title": detail_data.get("title"),
            "content": detail_data.get("desc") or detail_data.get("content"),
            "images": detail_data.get("imageList", []) or detail_data.get("images", []),
            "video": detail_data.get("video"),
            "author": {
                "user_id": detail_data.get("user", {}).get("userId"),
                "nickname": detail_data.get("user", {}).get("nickname"),
                "avatar": detail_data.get("user", {}).get("avatar"),
                "description": detail_data.get("user", {}).get("description"),
            },
            "likes": detail_data.get("likedCount", 0),
            "collects": detail_data.get("collectCount", 0),
            "comments": detail_data.get("commentCount", 0),
            "comments_list": [],
        }

    def _get_detail_message(self, detail_data: dict) -> str:
        """生成详情消息"""
        title = detail_data.get("title")
        if title:
            return f"获取笔记详情成功: {title[:20]}..."
        return "获取笔记详情成功"



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

    result = await tool.execute(params, ctx)

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
"""
小红书回复评论工具

实现 xhs_reply_comment 工具，回复评论。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business import business_tool
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSReplyCommentParams
from .result import XHSReplyCommentResult


@business_tool(name="xhs_reply_comment", site_type=XiaohongshuSite, param_type=XHSReplyCommentParams, operation_category="interact")
class ReplyCommentTool(BusinessTool):
    """
    小红书回复评论工具

    支持回复其他用户的评论。

    Usage:
        tool = ReplyCommentTool()
        result = await tool.execute(
            params=XHSReplyCommentParams(
                comment_id="comment123",
                content="说得对！"
            ),
            context=context
        )

        if result.success:
            print(f"回复成功")
    """

    name = "xhs_reply_comment"
    description = "回复小红书评论"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "interact"
    site_type = XiaohongshuSite
    required_login = True

    # 使用基类的 tab 管理抽象
    target_site_domain = "xiaohongshu.com"

    @log_operation("xhs_reply_comment")
    async def _execute_core(
        self,
        params: XHSReplyCommentParams,
        context: ExecutionContext
    ) -> Any:
        """
        核心执行逻辑

        Args:
            params: 工具参数
            context: 执行上下文
            site: 网站适配器实例

        Returns:
            XHSReplyCommentResult: 回复结果
        """
        # 从 context 获取 client（依赖注入）
        client = getattr(context, 'client', None)

        # ========== 使用 ensure_site_tab 获取标签页 ==========
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url="https://www.xiaohongshu.com/",
            params_tab_id=params.tab_id
        )

        if not tab_id:
            return XHSReplyCommentResult(
                success=False,
                comment_id=params.comment_id,
                content=params.content,
                message="无法获取标签页，请确保浏览器已打开"
            )

        # 直接使用 client 执行浏览器操作
        reply_result = await client.execute_tool("browser.control", {
            "action": "reply_comment",
            "params": {
                "comment_id": params.comment_id,
                "content": params.content,
                "tab_id": tab_id
            }
        }, timeout=15000)

        if not reply_result.get("success"):
            return XHSReplyCommentResult(
                success=False,
                comment_id=params.comment_id,
                content=params.content,
                message=f"回复失败: {reply_result.get('error', '未知错误')}"
            )

        return XHSReplyCommentResult(
            success=True,
            reply_id=reply_result.get("data", {}).get("reply_id") if reply_result.get("data") else None,
            comment_id=params.comment_id,
            content=params.content,
            message=self._get_reply_message(params.content)
        )

    def _get_reply_message(self, content: str) -> str:
        """生成回复消息"""
        preview = content[:20] + "..." if len(content) > 20 else content
        return f"回复成功: {preview}"

# 便捷函数
async def reply_comment(
    comment_id: str,
    content: str,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSReplyCommentResult:
    """
    便捷的回复评论函数

    Args:
        comment_id: 评论 ID
        content: 回复内容
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSReplyCommentResult: 回复结果
    """
    tool = ReplyCommentTool()
    params = XHSReplyCommentParams(
        tab_id=tab_id,
        comment_id=comment_id,
        content=content
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSReplyCommentResult(
            success=False,
            comment_id=comment_id,
            content=content,
            message=f"回复失败: {result.error}"
        )


__all__ = [
    "ReplyCommentTool",
    "reply_comment",
    "XHSReplyCommentParams",
    "XHSReplyCommentResult",
]
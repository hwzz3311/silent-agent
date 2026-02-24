"""
小红书回复评论工具

实现 xhs_reply_comment 工具，回复评论。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.errors import BusinessException
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSReplyCommentParams
from .result import XHSReplyCommentResult


class ReplyCommentTool(BusinessTool[XiaohongshuSite, XHSReplyCommentParams]):
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

    @log_operation("xhs_reply_comment")
    async def _execute_core(
        self,
        params: XHSReplyCommentParams,
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
            XHSReplyCommentResult: 回复结果
        """
        # 调用网站适配器的回复评论方法
        reply_result = await site.reply_comment(
            context,
            comment_id=params.comment_id,
            content=params.content
        )

        if not reply_result.success:
            return XHSReplyCommentResult(
                success=False,
                comment_id=params.comment_id,
                content=params.content,
                message=f"回复失败: {reply_result.error}"
            )

        return XHSReplyCommentResult(
            success=True,
            reply_id=reply_result.data.get("reply_id") if reply_result.data else None,
            comment_id=params.comment_id,
            content=params.content,
            message=self._get_reply_message(params.content)
        )

    def _get_reply_message(self, content: str) -> str:
        """生成回复消息"""
        preview = content[:20] + "..." if len(content) > 20 else content
        return f"回复成功: {preview}"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


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
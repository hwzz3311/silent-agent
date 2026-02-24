"""
小红书发表评论工具

实现 xhs_post_comment 工具，对笔记发表评论。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.errors import BusinessException
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSPostCommentParams
from .result import XHSPostCommentResult


class PostCommentTool(BusinessTool[XiaohongshuSite, XHSPostCommentParams]):
    """
    小红书发表评论工具

    支持对笔记发表评论，可@用户。

    Usage:
        tool = PostCommentTool()
        result = await tool.execute(
            params=XHSPostCommentParams(
                note_id="abc123",
                content="写得真好！",
                at_users=["user1", "user2"]
            ),
            context=context
        )

        if result.success:
            print(f"评论成功，评论ID: {result.data.comment_id}")
    """

    name = "xhs_post_comment"
    description = "对小红书笔记发表评论，支持@用户"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "interact"
    site_type = XiaohongshuSite
    required_login = True

    @log_operation("xhs_post_comment")
    async def _execute_core(
        self,
        params: XHSPostCommentParams,
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
            XHSPostCommentResult: 评论结果
        """
        # 调用网站适配器的评论方法
        comment_result = await site.post_comment(
            context,
            note_id=params.note_id,
            content=params.content,
            at_users=params.at_users
        )

        if not comment_result.success:
            return XHSPostCommentResult(
                success=False,
                note_id=params.note_id,
                content=params.content,
                message=f"评论失败: {comment_result.error}"
            )

        return XHSPostCommentResult(
            success=True,
            comment_id=comment_result.data.get("comment_id") if comment_result.data else None,
            note_id=params.note_id,
            content=params.content,
            message=self._get_comment_message(params.content)
        )

    def _get_comment_message(self, content: str) -> str:
        """生成评论消息"""
        preview = content[:20] + "..." if len(content) > 20 else content
        return f"评论成功: {preview}"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def post_comment(
    note_id: str,
    content: str,
    at_users: list = None,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSPostCommentResult:
    """
    便捷的发表评论函数

    Args:
        note_id: 笔记 ID
        content: 评论内容
        at_users: @用户列表
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSPostCommentResult: 评论结果
    """
    tool = PostCommentTool()
    params = XHSPostCommentParams(
        tab_id=tab_id,
        note_id=note_id,
        content=content,
        at_users=at_users
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSPostCommentResult(
            success=False,
            note_id=note_id,
            content=content,
            message=f"评论失败: {result.error}"
        )


__all__ = [
    "PostCommentTool",
    "post_comment",
    "XHSPostCommentParams",
    "XHSPostCommentResult",
]
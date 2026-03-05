"""
小红书发表评论工具

实现 xhs_post_comment 工具，对笔记发表评论。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business import business_tool
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSPostCommentParams
from .result import XHSPostCommentResult


@business_tool(name="xhs_post_comment", site_type=XiaohongshuSite, operation_category="interact")
class PostCommentTool(BusinessTool[XHSPostCommentParams]):
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

    # 使用基类的 tab 管理抽象
    target_site_domain = "xiaohongshu.com"

    @log_operation("xhs_post_comment")
    async def _execute_core(
        self,
        params: XHSPostCommentParams,
        context: ExecutionContext
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
            return XHSPostCommentResult(
                success=False,
                note_id=params.note_id,
                content=params.content,
                message="无法获取标签页，请确保浏览器已打开"
            )

        # 直接使用 client 执行浏览器操作
        comment_result = await client.execute_tool("browser.control", {
            "action": "post_comment",
            "params": {
                "note_id": params.note_id,
                "content": params.content,
                "at_users": params.at_users,
                "tab_id": tab_id
            }
        }, timeout=15000)

        if not comment_result.get("success"):
            return XHSPostCommentResult(
                success=False,
                note_id=params.note_id,
                content=params.content,
                message=f"评论失败: {comment_result.get('error', '未知错误')}"
            )

        return XHSPostCommentResult(
            success=True,
            comment_id=comment_result.get("data", {}).get("comment_id") if comment_result.get("data") else None,
            note_id=params.note_id,
            content=params.content,
            message=self._get_comment_message(params.content)
        )

    def _get_comment_message(self, content: str) -> str:
        """生成评论消息"""
        preview = content[:20] + "..." if len(content) > 20 else content
        return f"评论成功: {preview}"

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
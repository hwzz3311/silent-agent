"""
小红书点赞工具

实现 xhs_like_feed 工具，点赞或取消点赞笔记。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSLikeFeedParams
from .result import XHSLikeFeedResult


class LikeFeedTool(BusinessTool[XiaohongshuSite, XHSLikeFeedParams]):
    """
    小红书点赞/取消点赞工具

    支持对笔记进行点赞或取消点赞操作。

    Usage:
        tool = LikeFeedTool()
        result = await tool.execute(
            params=XHSLikeFeedParams(
                note_id="abc123",
                action="like"
            ),
            context=context
        )

        if result.success:
            print(f"点赞成功")
    """

    name = "xhs_like_feed"
    description = "点赞或取消点赞小红书笔记"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "interact"
    site_type = XiaohongshuSite
    required_login = True

    @log_operation("xhs_like_feed")
    async def _execute_core(
        self,
        params: XHSLikeFeedParams,
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
            XHSLikeFeedResult: 操作结果
        """
        # 调用网站适配器的点赞方法
        like_result = await site.like_feed(
            context,
            note_id=params.note_id,
            action=params.action
        )

        if not like_result.success:
            return XHSLikeFeedResult(
                success=False,
                note_id=params.note_id,
                action=params.action,
                message=f"点赞失败: {like_result.error}"
            )

        return XHSLikeFeedResult(
            success=True,
            note_id=params.note_id,
            action=params.action,
            message=self._get_like_message(params.action)
        )

    def _get_like_message(self, action: str) -> str:
        """生成点赞消息"""
        if action == "like":
            return "点赞成功"
        elif action == "unlike":
            return "取消点赞成功"
        else:
            return f"操作成功: {action}"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def like_feed(
    note_id: str,
    action: str = "like",
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSLikeFeedResult:
    """
    便捷的点赞函数

    Args:
        note_id: 笔记 ID
        action: 操作类型（like/unlike）
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSLikeFeedResult: 操作结果
    """
    tool = LikeFeedTool()
    params = XHSLikeFeedParams(
        tab_id=tab_id,
        note_id=note_id,
        action=action
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSLikeFeedResult(
            success=False,
            note_id=note_id,
            action=action,
            message=f"操作失败: {result.error}"
        )


__all__ = [
    "LikeFeedTool",
    "like_feed",
    "XHSLikeFeedParams",
    "XHSLikeFeedResult",
]
"""
小红书检查发布状态工具

实现 xhs_check_publish_status 工具，检查笔记发布状态。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSCheckPublishStatusParams
from .result import XHSCheckPublishStatusResult


class CheckPublishStatusTool(BusinessTool[XiaohongshuSite, XHSCheckPublishStatusParams]):
    """
    小红书检查发布状态工具

    检查笔记的发布状态，支持查看草稿、已发布、失败等状态。

    Usage:
        tool = CheckPublishStatusTool()
        result = await tool.execute(
            params=XHSCheckPublishStatusParams(note_id="abc123"),
            context=context
        )

        if result.success:
            print(f"状态: {result.data.status}")
    """

    name = "xhs_check_publish_status"
    description = "检查小红书笔记发布状态"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "publish"
    site_type = XiaohongshuSite
    required_login = True

    @log_operation("xhs_check_publish_status")
    async def _execute_core(
        self,
        params: XHSCheckPublishStatusParams,
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
            XHSCheckPublishStatusResult: 检查结果
        """
        # 调用网站适配器的检查发布状态方法
        status_result = await site.check_publish_status(
            context,
            note_id=params.note_id
        )

        if not status_result.success:
            return XHSCheckPublishStatusResult(
                success=False,
                message=f"检查发布状态失败: {status_result.error}"
            )

        # 解析状态结果
        result_data = status_result.data if isinstance(status_result.data, dict) else {}

        return XHSCheckPublishStatusResult(
            success=True,
            note_id=result_data.get("note_id") or params.note_id,
            status=result_data.get("status", "unknown"),
            publish_time=result_data.get("publish_time"),
            views=result_data.get("views", 0),
            likes=result_data.get("likes", 0),
            message=self._get_status_message(result_data)
        )

    def _get_status_message(self, result_data: dict) -> str:
        """生成状态消息"""
        status = result_data.get("status", "unknown")
        status_names = {
            "draft": "草稿",
            "scheduled": "已定时",
            "publishing": "发布中",
            "published": "已发布",
            "failed": "发布失败",
            "unknown": "未知"
        }
        status_name = status_names.get(status, status)

        views = result_data.get("views", 0)
        likes = result_data.get("likes", 0)

        message = f"状态: {status_name}"
        if status == "published":
            message += f"，浏览: {views}，点赞: {likes}"

        return message

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def check_publish_status(
    note_id: str = None,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSCheckPublishStatusResult:
    """
    便捷的检查发布状态函数

    Args:
        note_id: 笔记 ID
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSCheckPublishStatusResult: 检查结果
    """
    tool = CheckPublishStatusTool()
    params = XHSCheckPublishStatusParams(
        tab_id=tab_id,
        note_id=note_id
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSCheckPublishStatusResult(
            success=False,
            message=f"检查失败: {result.error}"
        )


__all__ = [
    "CheckPublishStatusTool",
    "check_publish_status",
    "XHSCheckPublishStatusParams",
    "XHSCheckPublishStatusResult",
]
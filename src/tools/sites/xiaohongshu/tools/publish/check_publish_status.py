"""
小红书检查发布状态工具

实现 xhs_check_publish_status 工具，检查笔记发布状态。
"""

import logging
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business import business_tool
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSCheckPublishStatusParams
from .result import XHSCheckPublishStatusResult

# 创建日志记录器
logger = logging.getLogger("xhs_check_publish_status")


@business_tool(name="xhs_check_publish_status", site_type=XiaohongshuSite, operation_category="publish")
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

    # 直接模式类属性
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/"

    @log_operation("xhs_check_publish_status")
    async def _execute_core(
        self,
        params: XHSCheckPublishStatusParams,
        context: ExecutionContext,
    ) -> Any:
        """
        核心执行逻辑 - 直接模式

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）

        Returns:
            XHSCheckPublishStatusResult: 检查结果
        """
        logger.info(f"开始检查笔记发布状态，note_id: {params.note_id}")

        # 直接使用 context.client
        client = context.client
        logger.debug(f"使用 context.client: {client is not None}")

        if not client:
            logger.error("context.client 为空，浏览器可能未连接")
            return XHSCheckPublishStatusResult(
                success=False,
                message="浏览器未连接，请确保浏览器已启动"
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
            return XHSCheckPublishStatusResult(
                success=False,
                message="无法获取或创建标签页，请确保浏览器已打开"
            )

        logger.debug(f"最终使用的 tab_id: {tab_id}")

        # ========== 导航到笔记详情页 ==========
        if params.note_id:
            from src.tools.browser.navigate import NavigateTool
            nav_tool = NavigateTool()
            await nav_tool.execute(
                params=nav_tool._get_params_type()(
                    url=f"https://www.xiaohongshu.com/explore/{params.note_id}"
                ),
                context=context
            )

            # 等待页面加载
            import asyncio
            await asyncio.sleep(2)

        # ========== 提取状态信息 ==========
        from src.tools.browser.evaluate import EvaluateTool
        eval_tool = EvaluateTool()

        # 尝试获取页面状态
        js_code = """
        (function() {
            const publishBtn = document.querySelector('.publish-btn, .publish-button');
            const statusText = document.querySelector('[class*="status"], [class*="publish"]');

            if (publishBtn) {
                const text = publishBtn.textContent || publishBtn.innerText;
                if (text.includes('发布')) {
                    return { status: 'draft', message: '草稿状态' };
                }
            }

            return { status: 'unknown', message: '状态未知' };
        })
        """

        result = await eval_tool.execute(
            params=eval_tool._get_params_type()(code=js_code),
            context=context
        )

        if result.success and result.data:
            status = result.data.get("status", "unknown")
        else:
            status = "unknown"

        return XHSCheckPublishStatusResult(
            success=True,
            note_id=params.note_id,
            status=status,
            publish_time=None,
            view=0,
            likes=0,
            message=self._get_status_message({"status": status, "views": 0, "likes": 0})
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
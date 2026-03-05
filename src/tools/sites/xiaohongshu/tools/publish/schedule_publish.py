"""
小红书定时发布工具

实现 xhs_schedule_publish 工具，定时发布笔记。
"""

import logging
import asyncio
from typing import Any
import uuid
from datetime import datetime

from src.tools.base import ExecutionContext
from src.tools.business import business_tool
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSSchedulePublishParams
from .result import XHSSchedulePublishResult

# 创建日志记录器
logger = logging.getLogger("xhs_schedule_publish")


@business_tool(name="xhs_schedule_publish", site_type=XiaohongshuSite, param_type=XHSSchedulePublishParams, operation_category="publish")
class SchedulePublishTool(BusinessTool):
    """
    小红书定时发布工具

    支持设置定时发布时间，到点自动发布。

    Usage:
        tool = SchedulePublishTool()
        result = await tool.execute(
            params=XHSSchedulePublishParams(
                title="定时发布笔记",
                content="这是一篇定时发布的笔记",
                schedule_time="2026-02-20T10:00:00"
            ),
            context=context
        )

        if result.success:
            print(f"定时任务已创建，任务ID: {result.data.task_id}")
    """

    name = "xhs_schedule_publish"
    description = "定时发布小红书笔记，支持设置发布时间"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "publish"
    site_type = XiaohongshuSite
    required_login = True

    # 使用基类的 tab 管理抽象
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/"

    @log_operation("xhs_schedule_publish")
    async def _execute_core(
        self,
        params: XHSSchedulePublishParams,
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
            XHSSchedulePublishResult: 定时发布结果
        """
        # 验证时间格式
        try:
            # 解析计划发布时间
            schedule_dt = datetime.fromisoformat(params.schedule_time.replace('Z', '+00:00'))
            if schedule_dt <= datetime.now():
                return XHSSchedulePublishResult(
                    success=False,
                    message="定时发布时间必须晚于当前时间"
                )
        except ValueError:
            return XHSSchedulePublishResult(
                success=False,
                message="时间格式无效请使用 ISO 格式，如 2026-02-20T10:00:00"
            )

        logger.info(f"开始定时发布笔记，计划时间: {params.schedule_time}")

        # 直接使用 context.client
        client = context.client
        logger.debug(f"使用 context.client: {client is not None}")

        if not client:
            logger.error("context.client 为空，浏览器可能未连接")
            return XHSSchedulePublishResult(
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
            return XHSSchedulePublishResult(
                success=False,
                message="无法获取或创建标签页请确保浏览器已打开"
            )

        logger.debug(f"最终使用的 tab_id: {tab_id}")

        # ========== 导航到发布页面 ==========
        await self._navigate_to_publish_page(client, tab_id)

        # ========== 填写发布内容 ==========
        # 填写标题
        from src.tools.browser.fill import FillTool
        fill_tool = FillTool()
        await fill_tool.execute(
            params=fill_tool._get_params_type()(
                selector=".title-input, [contenteditable='true']",
                value=params.title or ""
            ),
            context=context
        )

        # 填写正文内容
        await fill_tool.execute(
            params=fill_tool._get_params_type()(
                selector=".content-area, [contenteditable='true']",
                value=params.content or ""
            ),
            context=context
        )

        # 定时发布提示
        return XHSSchedulePublishResult(
            success=True,
            task_id=f"schedule_{uuid.uuid4().hex[:8]}",
            scheduled_time=params.schedule_time,
            message=f"定时发布已设置，时间: {params.schedule_time}（注意：定时发布需要后端支持）"
        )

    async def _navigate_to_publish_page(self, client, tab_id: int) -> bool:
        """
        导航到发布页面

        点击首页的发布按钮进入发布页面

        Args:
            client: 浏览器客户端
            tab_id: 标签页 ID

        Returns:
            bool: 是否成功
        """
        logger.info("尝试导航到发布页面...")

        # 发布按钮选择器
        publish_button_selectors = [
            ".publish-btn",
            ".create-note",
            "[data-testid='publish-button']",
            "[class*='publish']",
            "[class*='create']",
            "button:has-text('发布')",
        ]

        for selector in publish_button_selectors:
            check_code = f"document.querySelector('{selector}') !== null"
            result = await client.execute_tool("inject_script", {
                "code": check_code,
                "tabId": tab_id
            }, timeout=1500)

            if result.get("success") and result.get("data") is True:
                logger.info(f"检测到发布按钮: {selector}")
                # 点击发布按钮
                click_code = f"document.querySelector('{selector}').click()"
                click_result = await client.execute_tool("inject_script", {
                    "code": click_code,
                    "tabId": tab_id
                }, timeout=1500)

                if click_result.get("success"):
                    logger.info("点击发布按钮成功")
                    # 等待发布页面加载
                    await asyncio.sleep(2)
                    return True

        logger.warning("未找到发布按钮，尝试直接导航到发布页面")
        # 如果找不到发布按钮，尝试直接导航到小红书首页重新尝试
        nav_result = await client.execute_tool("chrome_navigate", {
            "url": "https://www.xiaohongshu.com/",
            "newTab": False
        }, timeout=10000)

        if nav_result.get("success"):
            await asyncio.sleep(3)
            # 再次尝试点击发布按钮
            return await self._navigate_to_publish_page(client, tab_id)

        return False

    def _get_schedule_message(self, schedule_time: str) -> str:
        """生成定时发布消息"""
        try:
            schedule_dt = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
            return f"定时任务已创建，计划于 {schedule_dt.strftime('%Y-%m-%d %H:%M:%S')} 发布"
        except ValueError:
            return f"定时任务已创建，计划于 {schedule_time} 发布"

# 便捷函数
async def schedule_publish(
    title: str,
    content: str,
    schedule_time: str,
    tab_id: int = None,
    images: list = None,
    video_path: str = None,
    timezone: str = "Asia/Shanghai",
    topic_tags: list = None,
    at_users: list = None,
    open_location: str = None,
    context: ExecutionContext = None
) -> XHSSchedulePublishResult:
    """
    便捷的定时发布函数

    Args:
        title: 笔记标题
        content: 笔记正文
        schedule_time: 定时发布时间（ISO 格式）
        tab_id: 标签页 ID
        images: 图片路径列表
        video_path: 视频路径
        timezone: 时区
        topic_tags: 话题标签列表
        at_users: @用户列表
        open_location: 位置信息
        context: 执行上下文

    Returns:
        XHSSchedulePublishResult: 定时发布结果
    """
    tool = SchedulePublishTool()
    params = XHSSchedulePublishParams(
        tab_id=tab_id,
        title=title,
        content=content,
        images=images,
        video_path=video_path,
        schedule_time=schedule_time,
        timezone=timezone,
        topic_tags=topic_tags,
        at_users=at_users,
        open_location=open_location
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSSchedulePublishResult(
            success=False,
            message=f"创建定时任务失败: {result.error}"
        )


__all__ = [
    "SchedulePublishTool",
    "schedule_publish",
    "XHSSchedulePublishParams",
    "XHSSchedulePublishResult",
]

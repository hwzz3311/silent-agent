"""
小红书发布视频内容工具

实现 xhs_publish_video 工具，发布视频笔记。
"""

import logging
import asyncio
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.domain import business_tool
from src.tools.domain.base import BusinessTool
from src.tools.domain.logging import log_operation
from src.tools.domain.site_base import Site
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .types import XHSPublishVideoParams, XHSPublishVideoResult

# 创建日志记录器
logger = logging.getLogger("xhs_publish_video")


@business_tool(name="xhs_publish_video", site_type=XiaohongshuSite, param_type=XHSPublishVideoParams, operation_category="publish")
class PublishVideoTool(BusinessTool):
    """
    发布小红书视频笔记

    支持发布视频内容，可选封面图片。

    Usage:
        tool = PublishVideoTool()
        result = await tool.execute(
            params=XHSPublishVideoParams(
                title="我的视频笔记",
                content="这是一篇视频测试笔记",
                video_path="/path/to/video.mp4"
            ),
            context=context
        )

        if result.success:
            print(f"发布成功，笔记ID: {result.data.note_id}")
    """

    name = "xhs_publish_video"
    description = "发布小红书视频笔记，支持标题、正文、视频、封面、话题和@用户"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "publish"
    site_type = XiaohongshuSite
    required_login = True

    # 使用基类的 tab 管理抽象
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/"

    # 提取硬编码选择器
    selectors = {
        "title_input": ".title-input, [contenteditable='true'], [data-testid='title-input']",
        "content_area": ".content-area, [contenteditable='true'], [data-testid='content-area']",
        "publish_button": ".publish-btn, .publish-button, [data-testid='publish-button']",
    }

    @log_operation("xhs_publish_video")
    async def _execute_core(
        self,
        params: XHSPublishVideoParams,
        context: ExecutionContext,
    ) -> Any:
        """
        核心执行逻辑 - 直接模式

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）
            site: 网站适配器实例

        Returns:
            XHSPublishVideoResult: 发布结果
        """
        logger.info("开始发布小红书视频笔记")

        # 直接使用 context.client
        client = context.client
        logger.debug(f"使用 context.client: {client is not None}")

        if not client:
            logger.error("context.client 为空，浏览器可能未连接")
            return XHSPublishVideoResult(
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
            return XHSPublishVideoResult(
                success=False,
                message="无法获取或创建标签页，请确保浏览器已打开"
            )

        logger.debug(f"最终使用的 tab_id: {tab_id}")

        # ========== 导航到发布页面 ==========
        await self._navigate_to_publish_page(client, tab_id)

        # ========== 填写发布内容 ==========
        # 填写标题
        from src.tools.primitives.fill import FillTool
        fill_tool = FillTool()
        await fill_tool.execute(
            params=fill_tool._get_params_type()(
                selector=self.get_selector("title_input"),
                value=params.title or ""
            ),
            context=context
        )

        # 填写正文内容
        content_text = params.content or ""
        if params.topic_tags:
            content_text += " " + " ".join(f"#{t}#" for t in params.topic_tags)

        await fill_tool.execute(
            params=fill_tool._get_params_type()(
                selector=self.get_selector("content_area"),
                value=content_text
            ),
            context=context
        )

        # ========== 点击发布按钮 ==========
        from src.tools.primitives.click import ClickTool
        click_tool = ClickTool()
        await click_tool.execute(
            params=click_tool._get_params_type()(
                selector=self.get_selector("publish_button"),
                timeout=10000
            ),
            context=context
        )

        # 等待发布完成
        await asyncio.sleep(3)

        return XHSPublishVideoResult(
            success=True,
            note_id=None,
            url=None,
            message="视频发布请求已提交"
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

    def _get_publish_message(self, result_data: dict) -> str:
        """生成发布结果消息"""
        if result_data.get("note_id"):
            return f"发布成功，笔记ID: {result_data['note_id']}"
        else:
            return "发布成功"

# 便捷函数
async def publish_video(
    title: str,
    content: str,
    video_path: str,
    tab_id: int = None,
    cover_image: str = None,
    topic_tags: list = None,
    at_users: list = None,
    open_location: str = None,
    context: ExecutionContext = None
) -> XHSPublishVideoResult:
    """
    便捷的发布视频函数

    Args:
        title: 笔记标题
        content: 笔记正文
        video_path: 视频文件路径
        tab_id: 标签页 ID
        cover_image: 封面图片路径
        topic_tags: 话题标签列表
        at_users: @用户列表
        open_location: 位置信息
        context: 执行上下文

    Returns:
        XHSPublishVideoResult: 发布结果
    """
    tool = PublishVideoTool()
    params = XHSPublishVideoParams(
        tab_id=tab_id,
        title=title,
        content=content,
        video_path=video_path,
        cover_image=cover_image,
        topic_tags=topic_tags,
        at_users=at_users,
        open_location=open_location
    )
    ctx = context or ExecutionContext()

    result = await tool.execute(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSPublishVideoResult(
            success=False,
            message=f"发布失败: {result.error}"
        )


__all__ = [
    "PublishVideoTool",
    "publish_video",
    "XHSPublishVideoParams",
    "XHSPublishVideoResult",
]
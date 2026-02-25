"""
小红书发布视频内容工具

实现 xhs_publish_video 工具，发布视频笔记。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSPublishVideoParams
from .result import XHSPublishVideoResult


class PublishVideoTool(BusinessTool[XiaohongshuSite, XHSPublishVideoParams]):
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

    @log_operation("xhs_publish_video")
    async def _execute_core(
        self,
        params: XHSPublishVideoParams,
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
            XHSPublishVideoResult: 发布结果
        """
        # 调用网站适配器的发布方法
        publish_result = await site.publish_video(
            context,
            title=params.title,
            content=params.content,
            video_path=params.video_path,
            cover_image=params.cover_image,
            topic_tags=params.topic_tags,
            at_users=params.at_users,
            open_location=params.open_location
        )

        if not publish_result.success:
            return XHSPublishVideoResult(
                success=False,
                message=f"发布失败: {publish_result.error}"
            )

        # 解析发布结果
        result_data = publish_result.data if isinstance(publish_result.data, dict) else {}

        return XHSPublishVideoResult(
            success=True,
            note_id=result_data.get("note_id"),
            url=result_data.get("url"),
            message=self._get_publish_message(result_data)
        )

    def _get_publish_message(self, result_data: dict) -> str:
        """生成发布结果消息"""
        if result_data.get("note_id"):
            return f"发布成功，笔记ID: {result_data['note_id']}"
        else:
            return "发布成功"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


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

    result = await tool.execute_with_retry(params, ctx)

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
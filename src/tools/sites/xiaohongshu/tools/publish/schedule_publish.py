"""
小红书定时发布工具

实现 xhs_schedule_publish 工具，定时发布笔记。
"""

from typing import Any
import uuid
from datetime import datetime

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.errors import BusinessException
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSSchedulePublishParams
from .result import XHSSchedulePublishResult


class SchedulePublishTool(BusinessTool[XiaohongshuSite, XHSSchedulePublishParams]):
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

    @log_operation("xhs_schedule_publish")
    async def _execute_core(
        self,
        params: XHSSchedulePublishParams,
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
                message=f"时间格式无效，请使用 ISO 格式，如 2026-02-20T10:00:00"
            )

        # 调用网站适配器的定时发布方法
        schedule_result = await site.schedule_publish(
            context,
            title=params.title,
            content=params.content,
            images=params.images,
            video_path=params.video_path,
            schedule_time=params.schedule_time,
            timezone=params.timezone,
            topic_tags=params.topic_tags,
            at_users=params.at_users,
            open_location=params.open_location
        )

        if not schedule_result.success:
            return XHSSchedulePublishResult(
                success=False,
                message=f"创建定时任务失败: {schedule_result.error}"
            )

        # 解析结果
        result_data = schedule_result.data if isinstance(schedule_result.data, dict) else {}

        return XHSSchedulePublishResult(
            success=True,
            task_id=result_data.get("task_id") or f"schedule_{uuid.uuid4().hex[:8]}",
            scheduled_time=params.schedule_time,
            message=self._get_schedule_message(params.schedule_time)
        )

    def _get_schedule_message(self, schedule_time: str) -> str:
        """生成定时发布消息"""
        try:
            schedule_dt = datetime.fromisoformat(schedule_time.replace('Z', '+00:00'))
            return f"定时任务已创建，计划于 {schedule_dt.strftime('%Y-%m-%d %H:%M:%S')} 发布"
        except ValueError:
            return f"定时任务已创建，计划于 {schedule_time} 发布"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


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
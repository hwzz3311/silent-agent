"""
小红书发布流程编排器

提供完整的小红书笔记/视频发布流程。

迁移自: src/tools/xhs/xiaohongshu_publisher.py
"""

import asyncio
from typing import Optional, Dict, Any, List
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result

# 从新框架 utils 导入工具
from ..utils import (
    set_files,
    download_video,
    transfer_video_to_page,
    intercept_upload,
)


class PublishNoteParams(ToolParameters):
    """发布图文笔记参数"""
    title: str = Field(
        ...,
        description="笔记标题"
    )
    content: str = Field(
        ...,
        description="笔记正文"
    )
    images: List[Dict[str, str]] = Field(
        default_factory=list,
        description="图片列表，每项包含 base64Data, fileName, mimeType"
    )
    topics: List[str] = Field(
        default_factory=list,
        description="话题标签列表"
    )
    tab_id: Optional[int] = Field(
        None,
        description="标签页 ID"
    )


class PublishVideoParams(ToolParameters):
    """发布视频参数"""
    video_url: str = Field(
        ...,
        description="视频下载地址 URL"
    )
    title: str = Field(
        ...,
        description="笔记标题"
    )
    content: str = Field(
        ...,
        description="笔记正文"
    )
    topics: List[str] = Field(
        default_factory=list,
        description="话题标签列表"
    )
    tab_id: Optional[int] = Field(
        None,
        description="标签页 ID"
    )


class PublishNoteResult:
    """发布图文笔记结果"""
    success: bool
    note_id: Optional[str]
    message: str
    steps: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "note_id": self.note_id,
            "message": self.message,
            "steps": self.steps
        }


class PublishVideoResult:
    """发布视频结果"""
    success: bool
    note_id: Optional[str]
    upload_url: Optional[str]
    message: str
    steps: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "note_id": self.note_id,
            "upload_url": self.upload_url,
            "message": self.message,
            "steps": self.steps
        }


@tool(
    name="xhs_publish",
    description="小红书笔记发布流程编排器（支持图文和视频）",
    category="workflow",
    version="1.0.0",
    tags=["xhs", "xiaohongshu", "publish", "workflow"]
)
class XiaohongshuPublisher(Tool[ToolParameters, Any]):
    """小红书发布流程编排器"""

    # 小红书相关选择器
    UPLOAD_SELECTOR = 'input[type="file"][accept*="image"]'
    TITLE_SELECTOR = '.note-editor .title-input, [contenteditable="true"]'
    CONTENT_SELECTOR = '.note-editor .content, [contenteditable="true"]'
    PUBLISH_SELECTOR = '.publish-button, button[type="submit"]'

    async def execute(
        self,
        params: ToolParameters,
        context: ExecutionContext
    ) -> Result[Any]:
        """执行发布流程"""
        try:
            if isinstance(params, PublishNoteParams):
                return await self._publish_note(params, context)
            elif isinstance(params, PublishVideoParams):
                return await self._publish_video(params, context)
            else:
                return self.fail("不支持的参数类型")
        except Exception as e:
            return self.error_from_exception(e)

    async def _publish_note(
        self,
        params: PublishNoteParams,
        context: ExecutionContext
    ) -> Result[PublishNoteResult]:
        """发布图文笔记流程"""
        from src.tools.browser.fill import FillTool
        from src.tools.browser.click import ClickTool

        steps = []
        tab_id = params.tab_id or context.tab_id

        try:
            fill_tool = FillTool()
            click_tool = ClickTool()

            # Step 1: 上传图片
            if params.images:
                steps.append({"step": "upload_images", "status": "pending"})

                result = await set_files(
                    selector=self.UPLOAD_SELECTOR,
                    files=params.images
                )

                if result.success:
                    steps.append({
                        "step": "upload_images",
                        "status": "success",
                        "file_count": len(params.images)
                    })
                else:
                    steps.append({
                        "step": "upload_images",
                        "status": "failed",
                        "message": result.error
                    })
                    return self.ok(PublishNoteResult(
                        success=False,
                        note_id=None,
                        message=f"图片上传失败: {result.error}",
                        steps=steps
                    ))
            else:
                steps.append({"step": "upload_images", "status": "skipped", "message": "无图片需要上传"})

            # Step 2: 填写标题
            steps.append({"step": "fill_title", "status": "pending"})

            await fill_tool.execute(
                params=self._get_fill_params(self.TITLE_SELECTOR, params.title),
                context=context
            )

            steps.append({"step": "fill_title", "status": "success", "value": params.title})

            # Step 3: 填写正文
            steps.append({"step": "fill_content", "status": "pending"})

            await fill_tool.execute(
                params=self._get_fill_params(self.CONTENT_SELECTOR, params.content),
                context=context
            )

            steps.append({"step": "fill_content", "status": "success", "value": params.content[:100]})

            # Step 4: 添加话题
            if params.topics:
                steps.append({"step": "add_topics", "status": "pending"})

                # 插入话题到正文
                topic_text = " " + " ".join(f"#{t}#" for t in params.topics)
                await fill_tool.execute(
                    params=self._get_fill_params(self.CONTENT_SELECTOR, params.content + topic_text),
                    context=context
                )

                steps.append({
                    "step": "add_topics",
                    "status": "success",
                    "topics": params.topics
                })
            else:
                steps.append({"step": "add_topics", "status": "skipped", "message": "无话题"})

            # Step 5: 点击发布
            steps.append({"step": "publish", "status": "pending"})

            await click_tool.execute(
                params=self._get_click_params(self.PUBLISH_SELECTOR),
                context=context
            )

            await asyncio.sleep(2)

            steps.append({"step": "publish", "status": "success"})

            return self.ok(PublishNoteResult(
                success=True,
                note_id="",
                message="笔记发布成功",
                steps=steps
            ))

        except Exception as e:
            steps.append({"step": "error", "status": "failed", "message": str(e)})
            return self.ok(PublishNoteResult(
                success=False,
                note_id=None,
                message=f"发布失败: {str(e)}",
                steps=steps
            ))

    async def _publish_video(
        self,
        params: PublishVideoParams,
        context: ExecutionContext
    ) -> Result[PublishVideoResult]:
        """发布视频流程"""
        from src.tools.browser.fill import FillTool
        from src.tools.browser.click import ClickTool

        steps = []
        tab_id = params.tab_id or context.tab_id

        try:
            fill_tool = FillTool()
            click_tool = ClickTool()

            # Step 1: 下载视频
            steps.append({"step": "download_video", "status": "pending"})

            download_result = await download_video(
                url=params.video_url
            )

            if download_result.success:
                steps.append({
                    "step": "download_video",
                    "status": "success",
                    "video_id": download_result.data.video_id
                })
            else:
                steps.append({
                    "step": "download_video",
                    "status": "failed",
                    "message": getattr(download_result.data, 'message', str(download_result.error))
                })
                return self.ok(PublishVideoResult(
                    success=False,
                    note_id=None,
                    upload_url=None,
                    message=f"视频下载失败: {download_result.error}",
                    steps=steps
                ))

            # Step 2: 传输视频到页面
            steps.append({"step": "transfer_video", "status": "pending"})

            transfer_result = await transfer_video_to_page(
                selector=self.UPLOAD_SELECTOR,
                tab_id=tab_id
            )

            if transfer_result.success:
                steps.append({
                    "step": "transfer_video",
                    "status": "success",
                    "chunks": transfer_result.data.chunks
                })
            else:
                steps.append({
                    "step": "transfer_video",
                    "status": "failed",
                    "message": getattr(transfer_result.data, 'message', str(transfer_result.error))
                })
                return self.ok(PublishVideoResult(
                    success=False,
                    note_id=None,
                    upload_url=None,
                    message=f"视频传输失败: {transfer_result.error}",
                    steps=steps
                ))

            # Step 3: 拦截上传获取 OSS 地址
            steps.append({"step": "intercept_upload", "status": "pending"})

            intercept_result = await intercept_upload(
                tab_id=tab_id
            )

            if intercept_result.success:
                steps.append({
                    "step": "intercept_upload",
                    "status": "success",
                    "upload_url": intercept_result.data.upload_url
                })
                upload_url = intercept_result.data.upload_url
            else:
                steps.append({
                    "step": "intercept_upload",
                    "status": "failed",
                    "message": getattr(intercept_result.data, 'message', str(intercept_result.error))
                })
                upload_url = None

            # Step 4: 填写标题
            steps.append({"step": "fill_title", "status": "pending"})

            await fill_tool.execute(
                params=self._get_fill_params(self.TITLE_SELECTOR, params.title),
                context=context
            )

            steps.append({"step": "fill_title", "status": "success", "value": params.title})

            # Step 5: 填写正文
            steps.append({"step": "fill_content", "status": "pending"})

            await fill_tool.execute(
                params=self._get_fill_params(self.CONTENT_SELECTOR, params.content),
                context=context
            )

            steps.append({"step": "fill_content", "status": "success", "value": params.content[:100]})

            # Step 6: 点击发布
            steps.append({"step": "publish", "status": "pending"})

            await click_tool.execute(
                params=self._get_click_params(self.PUBLISH_SELECTOR),
                context=context
            )

            await asyncio.sleep(2)

            steps.append({"step": "publish", "status": "success"})

            return self.ok(PublishVideoResult(
                success=True,
                note_id="",
                upload_url=upload_url,
                message="视频发布成功",
                steps=steps
            ))

        except Exception as e:
            steps.append({"step": "error", "status": "failed", "message": str(e)})
            return self.ok(PublishVideoResult(
                success=False,
                note_id=None,
                upload_url=None,
                message=f"发布失败: {str(e)}",
                steps=steps
            ))

    def _get_fill_params(self, selector: str, value: str):
        """创建填充参数"""
        from src.tools.browser.fill import FillParams
        return FillParams(selector=selector, value=value)

    def _get_click_params(self, selector: str):
        """创建点击参数"""
        from src.tools.browser.click import ClickParams
        return ClickParams(selector=selector)

    # 便捷方法
    def get_upload_input_selector(self) -> str:
        """获取上传输入框选择器"""
        return self.UPLOAD_SELECTOR

    def get_publish_button_selector(self) -> str:
        """获取发布按钮选择器"""
        return self.PUBLISH_SELECTOR

    def get_title_input_selector(self) -> str:
        """获取标题输入框选择器"""
        return self.TITLE_SELECTOR

    def get_content_input_selector(self) -> str:
        """获取正文输入框选择器"""
        return self.CONTENT_SELECTOR


# ========== 便捷函数 ==========

async def publish_note(
    title: str,
    content: str,
    images: List[Dict[str, str]] = None,
    topics: List[str] = None,
    tab_id: int = None,
    context: ExecutionContext = None
) -> Result[PublishNoteResult]:
    """发布图文笔记"""
    params = PublishNoteParams(
        title=title,
        content=content,
        images=images or [],
        topics=topics or [],
        tab_id=tab_id
    )
    tool = XiaohongshuPublisher()
    return await tool.execute(params, context or ExecutionContext())


async def publish_video(
    video_url: str,
    title: str,
    content: str,
    topics: List[str] = None,
    tab_id: int = None,
    context: ExecutionContext = None
) -> Result[PublishVideoResult]:
    """发布视频"""
    params = PublishVideoParams(
        video_url=video_url,
        title=title,
        content=content,
        topics=topics or [],
        tab_id=tab_id
    )
    tool = XiaohongshuPublisher()
    return await tool.execute(params, context or ExecutionContext())


__all__ = [
    "XiaohongshuPublisher",
    "PublishNoteParams",
    "PublishVideoParams",
    "PublishNoteResult",
    "PublishVideoResult",
    "publish_note",
    "publish_video",
]
"""
视频上传拦截工具

拦截视频上传请求，获取 OSS 上传地址。

迁移自: src/tools/xhs/video_upload_intercept.py
"""

import asyncio
import json
from typing import Optional, Dict, Any
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result

# 复用 video_transfer.py 中的视频暂存管理
from .video_transfer import get_video_store


class VideoUploadInterceptParams(ToolParameters):
    """视频上传拦截参数"""
    tab_id: Optional[int] = Field(
        None,
        description="标签页 ID"
    )
    timeout: Optional[int] = Field(
        60000,
        description="等待上传 URL 的超时时间（毫秒）"
    )
    clear_after_upload: bool = Field(
        False,
        description="上传后是否清除暂存视频"
    )


class VideoUploadInterceptResult:
    """视频上传拦截结果"""
    success: bool
    file_name: str
    file_size: int
    upload_url: str
    message: str
    need_upload: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "upload_url": self.upload_url,
            "message": self.message,
            "need_upload": self.need_upload
        }


@tool(
    name="xhs_video_upload_intercept",
    description="拦截小红书视频上传请求，获取 OSS 上传地址",
    category="network",
    version="1.0.0",
    tags=["xhs", "xiaohongshu", "video", "upload", "intercept"]
)
class VideoUploadInterceptTool(Tool[VideoUploadInterceptParams, VideoUploadInterceptResult]):
    """视频上传拦截工具"""

    async def execute(
        self,
        params: VideoUploadInterceptParams,
        context: ExecutionContext
    ) -> Result[VideoUploadInterceptResult]:
        """执行上传拦截"""
        try:
            # 检查是否有暂存的视频
            store = get_video_store()
            stored_video = store.get()

            if not stored_video:
                return self.ok(VideoUploadInterceptResult(
                    success=False,
                    file_name="",
                    file_size=0,
                    upload_url="",
                    message="没有暂存的视频，请先下载视频",
                    need_upload=True
                ))

            # 获取标签页 ID
            tab_id = params.tab_id or context.tab_id
            if not tab_id:
                from src.relay_client import SilentAgentClient
                client = SilentAgentClient()
                try:
                    page_info = await client.call_tool("chrome_get_page_info")
                    tab_id = page_info.get("tabId")
                except Exception:
                    pass

            if not tab_id:
                return self.fail("无法确定标签页 ID")

            # 执行拦截
            result = await self._intercept_upload(
                stored_video=stored_video,
                tab_id=tab_id,
                timeout=params.timeout
            )

            # 如果需要清除暂存
            if params.clear_after_upload and result.success:
                store.clear(stored_video.video_id)

            return self.ok(result)

        except Exception as e:
            return self.error_from_exception(e)

    async def _intercept_upload(
        self,
        stored_video,
        tab_id: int,
        timeout: int
    ) -> VideoUploadInterceptResult:
        """执行拦截逻辑"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            # 1. 注入拦截器
            inject_code = self._create_interceptor_code(stored_video)
            await client.call_tool(
                "inject_script",
                code=inject_code,
                world="MAIN"
            )

            # 2. 触发上传
            trigger_code = self._create_trigger_code()
            await client.call_tool(
                "inject_script",
                code=trigger_code,
                world="MAIN"
            )

            # 等待并获取上传信息
            await asyncio.sleep(3)  # 等待上传开始

            # 3. 获取上传 URL
            upload_info = await self._get_upload_info(
                client=client,
                tab_id=tab_id,
                timeout=timeout
            )

            if upload_info.success:
                return VideoUploadInterceptResult(
                    success=True,
                    file_name=stored_video.file_name,
                    file_size=stored_video.file_size,
                    upload_url=upload_info.upload_url,
                    message="获取上传地址成功"
                )
            else:
                return VideoUploadInterceptResult(
                    success=False,
                    file_name=stored_video.file_name,
                    file_size=stored_video.file_size,
                    upload_url="",
                    message=upload_info.message
                )

        except Exception as e:
            return VideoUploadInterceptResult(
                success=False,
                file_name=stored_video.file_name,
                file_size=stored_video.file_size,
                upload_url="",
                message=f"拦截失败: {str(e)}"
            )

    def _create_interceptor_code(self, stored_video) -> str:
        """创建拦截器的 JavaScript 代码"""
        data_json = json.dumps(list(stored_video.data))

        return f"""
        (function() {{
            // 存储视频数据到 window
            window.__xhsInterceptedVideo = {{
                data: new Uint8Array({data_json}),
                fileName: "{stored_video.file_name}",
                fileType: "{stored_video.file_type}"
            }};

            // XHR 拦截器
            const OriginalXHROpen = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url, ...args) {{
                this.__xhsUrl = url.toString();
                if (url.toString().includes('upload') || url.toString().includes('video')) {{
                    this.__xhsIsUpload = true;
                }}
                return OriginalXHROpen.apply(this, [method, url, ...args]);
            }};

            // Fetch 拦截器
            const OriginalFetch = window.fetch;
            window.fetch = async function(url, options) {{
                const urlStr = typeof url === 'string' ? url : url.url;
                if (urlStr.includes('upload') || urlStr.includes('video') || urlStr.includes('media')) {{
                    try {{
                        const response = await OriginalFetch.apply(this, [url, options]);
                        const clonedResponse = response.clone();
                        try {{
                            const data = await clonedResponse.json();
                            // 提取 uploadUrl
                            const uploadUrl = data?.data?.uploadUrl || data.uploadUrl || data.url;
                            if (uploadUrl) {{
                                window.__xhsUploadInfo = {{
                                    uploadUrl: uploadUrl,
                                    timestamp: Date.now()
                                }};
                            }}
                        }} catch(e) {{}}
                        return response;
                    }} catch(e) {{
                        throw e;
                    }}
                }}
                return OriginalFetch.apply(this, [url, options]);
            }};

            return {{ success: true, message: "拦截器已设置" }};
        }})()
        """

    def _create_trigger_code(self) -> str:
        """创建触发上传的 JavaScript 代码"""
        return """
        (function() {
            try {
                // 查找小红书的上传相关元素
                const uploadElement = document.querySelector('.upload-content') ||
                                     document.querySelector('.upload-wrapper') ||
                                     document.querySelector('[class*="upload"]') ||
                                     document.querySelector('input[type="file"][accept*="video"]') ||
                                     document.querySelector('.upload-input');

                if (uploadElement) {
                    uploadElement.click();
                    return { triggered: true, message: "已点击上传元素" };
                } else {
                    return { triggered: false, message: "未找到上传元素" };
                }
            } catch (e) {
                return { error: { message: e.message } };
            }
        })()
        """

    async def _get_upload_info(
        self,
        client,
        tab_id: int,
        timeout: int
    ) -> Dict[str, Any]:
        """获取上传信息"""
        try:
            result = await client.call_tool(
                "inject_script",
                code="""
                (function() {
                    if (window.__xhsUploadInfo) {
                        return window.__xhsUploadInfo;
                    }
                    return null;
                })()
                """,
                world="MAIN"
            )

            if result and isinstance(result, dict):
                content = result.get("content", [])
                if content:
                    text = content[0].get("text", "")
                    if text and text != "null":
                        info = json.loads(text)
                        return {
                            "success": True,
                            "upload_url": info.get("uploadUrl", "")
                        }

            return {
                "success": False,
                "message": "未获取到上传地址"
            }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


# ========== 便捷函数 ==========

async def intercept_upload(
    tab_id: Optional[int] = None,
    timeout: int = 60000,
    clear_after_upload: bool = False,
    context: ExecutionContext = None
) -> Result[VideoUploadInterceptResult]:
    """拦截视频上传请求"""
    params = VideoUploadInterceptParams(
        tab_id=tab_id,
        timeout=timeout,
        clear_after_upload=clear_after_upload
    )
    tool = VideoUploadInterceptTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = [
    "VideoUploadInterceptTool",
    "VideoUploadInterceptParams",
    "VideoUploadInterceptResult",
    "intercept_upload",
]
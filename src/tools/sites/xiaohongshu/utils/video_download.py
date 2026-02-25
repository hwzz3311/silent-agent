"""
视频下载工具

提供从 URL 下载视频并暂存到本地的功能。

迁移自: src/tools/xhs/video_download.py
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result

# 复用 video_transfer.py 中的视频暂存管理
from .video_transfer import (
    VideoStore,
    get_video_store,
)


# ========== 下载参数 ==========

class VideoDownloadParams(ToolParameters):
    """视频下载参数"""
    url: str = Field(
        ...,
        description="视频下载地址 URL"
    )
    timeout: Optional[int] = Field(
        1800000,  # 30分钟
        description="下载超时时间（毫秒）"
    )
    tab_id: Optional[int] = Field(
        None,
        description="标签页 ID（用于在页面显示进度）"
    )
    video_id: Optional[str] = Field(
        None,
        description="视频 ID（用于标识暂存视频）"
    )


class VideoDownloadResult:
    """视频下载结果"""
    video_id: str
    file_name: str
    file_type: str
    file_size: int
    success: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "success": self.success,
            "message": self.message
        }


@tool(
    name="xhs_video_download",
    description="从小红书或其他支持的 URL 下载视频并暂存到本地",
    category="network",
    version="1.0.0",
    tags=["xhs", "xiaohongshu", "video", "download"]
)
class VideoDownloadTool(Tool[VideoDownloadParams, VideoDownloadResult]):
    """视频下载工具"""

    MAX_FILE_SIZE = 20 * 1024 * 1024 * 1024  # 20GB
    CHUNK_SIZE = 20 * 1024 * 1024  # 20MB
    PROGRESS_UPDATE_INTERVAL = 500  # 500ms

    async def execute(
        self,
        params: VideoDownloadParams,
        context: ExecutionContext
    ) -> Result[VideoDownloadResult]:
        """执行视频下载"""
        try:
            # 获取视频暂存管理器
            store = get_video_store()

            # 执行下载
            result = await self._download_video(
                url=params.url,
                timeout=params.timeout,
                tab_id=params.tab_id or context.tab_id,
                store=store
            )

            return self.ok(result)

        except Exception as e:
            return self.error_from_exception(e)

    async def _download_video(
        self,
        url: str,
        timeout: int,
        tab_id: Optional[int],
        store: VideoStore
    ) -> VideoDownloadResult:
        """执行下载逻辑"""
        import aiohttp

        start_time = datetime.now()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout / 1000)
                ) as response:

                    if not response.ok:
                        return VideoDownloadResult(
                            video_id="",
                            file_name="",
                            file_type="",
                            file_size=0,
                            success=False,
                            message=f"下载失败: HTTP {response.status}"
                        )

                    # 检查内容类型
                    content_type = response.headers.get("Content-Type", "")
                    if not self._is_valid_video_type(content_type):
                        # 尝试从 URL 判断
                        pass

                    # 检查文件大小
                    content_length = response.headers.get("Content-Length")
                    file_size = 0
                    if content_length:
                        file_size = int(content_length)
                        if file_size > self.MAX_FILE_SIZE:
                            return VideoDownloadResult(
                                video_id="",
                                file_name="",
                                file_type="",
                                file_size=0,
                                success=False,
                                message=f"文件过大: {file_size / 1024 / 1024 / 1024:.2f}GB，最大支持 20GB"
                            )

                    # 下载数据
                    data = bytearray()
                    downloaded_size = 0
                    last_progress_time = start_time

                    async for chunk in response.content.iter_chunked(self.CHUNK_SIZE):
                        data.extend(chunk)
                        downloaded_size += len(chunk)

                        # 更新进度
                        current_time = datetime.now()
                        if (current_time - last_progress_time).total_seconds() * 1000 >= self.PROGRESS_UPDATE_INTERVAL:
                            last_progress_time = current_time

                            # 在页面显示进度（如果指定了 tab_id）
                            if tab_id:
                                await self._show_progress(
                                    tab_id=tab_id,
                                    downloaded=downloaded_size,
                                    total=file_size if content_length else 0,
                                    speed=self._calculate_speed(
                                        downloaded_size,
                                        (current_time - start_time).total_seconds()
                                    )
                                )

                    # 提取文件名和类型（使用 store 的方法）
                    file_name = store._extract_file_name(url)
                    file_type = store._get_file_type(file_name, bytes(data))

                    # 存储视频
                    stored = store.store(
                        url=url,
                        data=bytes(data),
                        file_name=file_name,
                        file_type=file_type
                    )

                    return VideoDownloadResult(
                        video_id=stored.video_id,
                        file_name=stored.file_name,
                        file_type=stored.file_type,
                        file_size=stored.file_size,
                        success=True,
                        message="视频下载并暂存成功"
                    )

            except asyncio.TimeoutError:
                return VideoDownloadResult(
                    video_id="",
                    file_name="",
                    file_type="",
                    file_size=0,
                    success=False,
                    message=f"下载超时（超过 {timeout / 1000 / 60:.0f} 分钟）"
                )
            except Exception as e:
                return VideoDownloadResult(
                    video_id="",
                    file_name="",
                    file_type="",
                    file_size=0,
                    success=False,
                    message=f"下载失败: {str(e)}"
                )

    async def _show_progress(
        self,
        tab_id: int,
        downloaded: int,
        total: int,
        speed: float
    ):
        """在页面显示下载进度"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            if total > 0:
                percent = (downloaded / total * 100)
                progress_text = f"正在下载视频... {percent:.1f}% ({downloaded / 1024 / 1024:.2f}MB / {total / 1024 / 1024:.2f}MB) {speed:.2f}MB/s"
            else:
                progress_text = f"正在下载视频... ({downloaded / 1024 / 1024:.2f}MB) {speed:.2f}MB/s"

            await client.call_tool(
                "inject_script",
                code=f"""
                (function() {{
                    if (typeof window.__showToast === 'function') {{
                        window.__showToast('{progress_text}');
                    }}
                }})()
                """,
                world="MAIN"
            )
        except Exception:
            pass

    def _calculate_speed(self, downloaded: int, elapsed: float) -> float:
        """计算下载速度（MB/s）"""
        if elapsed <= 0:
            return 0
        return (downloaded / 1024 / 1024) / elapsed

    def _is_valid_video_type(self, content_type: str) -> bool:
        """检查是否是有效的视频类型"""
        valid_types = [
            "video/mp4",
            "video/quicktime",
            "video/x-msvideo",
            "video/webm",
            "video/x-matroska",
            "application/octet-stream"
        ]
        return any(content_type.startswith(t) for t in valid_types)


# ========== 便捷函数 ==========

async def download_video(
    url: str,
    timeout: int = 1800000,
    tab_id: Optional[int] = None,
    video_id: Optional[str] = None,
    context: ExecutionContext = None
) -> Result[VideoDownloadResult]:
    """下载视频"""
    params = VideoDownloadParams(
        url=url,
        timeout=timeout,
        tab_id=tab_id,
        video_id=video_id
    )
    tool = VideoDownloadTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = [
    "VideoDownloadTool",
    "VideoDownloadParams",
    "VideoDownloadResult",
    "download_video",
]
"""
视频分块传输工具

将暂存的视频分块传输到页面并设置到文件输入框。

迁移自: src/tools/xhs/video_chunk_transfer.py
"""

import asyncio
import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


# ========== 视频暂存管理 ==========

@dataclass
class StoredVideo:
    """暂存的视频信息"""
    video_id: str
    file_name: str
    file_type: str
    file_size: int
    data: bytes
    stored_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_expired(self, expiration_minutes: int = 30) -> bool:
        """检查是否已过期"""
        return datetime.now() - self.stored_at > timedelta(minutes=expiration_minutes)


class VideoStore:
    """视频暂存管理器"""

    def __init__(self, storage_dir: str = "~/.neurone/videos"):
        self.storage_dir = Path(storage_dir).expanduser()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, StoredVideo] = {}

        # 加载已有的暂存视频
        self._load_existing()

    def _load_existing(self):
        """加载已有的暂存视频"""
        try:
            for video_file in self.storage_dir.glob("*.meta.json"):
                video_id = video_file.stem.replace(".meta", "")
                data_file = self.storage_dir / f"{video_id}.data"

                if data_file.exists():
                    try:
                        with open(video_file, 'r') as f:
                            meta = json.load(f)

                        with open(data_file, 'rb') as f:
                            data = f.read()

                        stored_video = StoredVideo(
                            video_id=video_id,
                            file_name=meta["file_name"],
                            file_type=meta["file_type"],
                            file_size=meta["file_size"],
                            data=data,
                            stored_at=datetime.fromisoformat(meta["stored_at"])
                        )

                        if not stored_video.is_expired():
                            self._cache[video_id] = stored_video
                        else:
                            self._cleanup_video(video_id)
                    except Exception:
                        self._cleanup_video(video_id)
        except Exception:
            pass

    def _cleanup_video(self, video_id: str):
        """清理视频文件"""
        try:
            meta_file = self.storage_dir / f"{video_id}.meta.json"
            data_file = self.storage_dir / f"{video_id}.data"

            if meta_file.exists():
                meta_file.unlink()
            if data_file.exists():
                data_file.unlink()
        except Exception:
            pass

    def store(
        self,
        url: str,
        data: bytes,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None
    ) -> StoredVideo:
        """
        存储视频

        Args:
            url: 下载来源 URL
            data: 视频数据
            file_name: 文件名（可选，从 URL 提取）
            file_type: 文件类型（可选，自动检测）

        Returns:
            StoredVideo 对象
        """
        video_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(url) % 100000:05d}"

        if not file_name:
            file_name = self._extract_file_name(url)

        if not file_type:
            file_type = self._get_file_type(file_name, data)

        stored = StoredVideo(
            video_id=video_id,
            file_name=file_name,
            file_type=file_type,
            file_size=len(data),
            data=data
        )

        self._cache[video_id] = stored
        self._save_to_disk(stored)
        self._cleanup_expired()

        return stored

    def get(self, video_id: Optional[str] = None) -> Optional[StoredVideo]:
        """
        获取暂存的视频

        Args:
            video_id: 视频 ID（可选，默认返回最新的视频）

        Returns:
            StoredVideo 对象或 None
        """
        if video_id:
            return self._cache.get(video_id)

        if self._cache:
            return max(self._cache.values(), key=lambda v: v.stored_at)
        return None

    def clear(self, video_id: Optional[str] = None):
        """清除暂存的视频"""
        if video_id:
            if video_id in self._cache:
                self._cleanup_video(video_id)
                del self._cache[video_id]
        else:
            for vid in list(self._cache.keys()):
                self._cleanup_video(vid)
            self._cache.clear()

    def list_videos(self) -> List[Dict[str, str]]:
        """列出所有暂存的视频"""
        return [
            {
                "video_id": v.video_id,
                "file_name": v.file_name,
                "file_type": v.file_type,
                "file_size": v.file_size,
                "stored_at": v.stored_at.isoformat()
            }
            for v in self._cache.values()
        ]

    def _save_to_disk(self, stored: StoredVideo):
        """保存到磁盘"""
        try:
            meta = {
                "video_id": stored.video_id,
                "file_name": stored.file_name,
                "file_type": stored.file_type,
                "file_size": stored.file_size,
                "stored_at": stored.stored_at.isoformat()
            }

            meta_file = self.storage_dir / f"{stored.video_id}.meta.json"
            with open(meta_file, 'w') as f:
                json.dump(meta, f)

            data_file = self.storage_dir / f"{stored.video_id}.data"
            with open(data_file, 'wb') as f:
                f.write(stored.data)

        except Exception:
            pass

    def _extract_file_name(self, url: str) -> str:
        """从 URL 提取文件名"""
        from urllib.parse import urlparse, unquote

        parsed = urlparse(url)
        path = unquote(parsed.path)
        file_name = path.split("/")[-1]

        if not file_name or "." not in file_name:
            file_name = f"downloaded_video_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"

        return file_name

    def _get_file_type(self, file_name: str, data: bytes) -> str:
        """获取文件类型"""
        extension = file_name.split(".")[-1].lower() if "." in file_name else ""

        extension_to_mime = {
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "avi": "video/x-msvideo",
            "webm": "video/webm",
            "mkv": "video/x-matroska",
        }

        if extension in extension_to_mime:
            return extension_to_mime[extension]

        if len(data) >= 12:
            if data[:4] == b"\x00\x00\x00" and data[4:8] == b"ftyp":
                return "video/mp4"
            if data[:4] == b"RIFF" and data[8:12] == b"AVI ":
                return "video/x-msvideo"
            if data[:4] == b"\x1A\x45\xDF\xA3":
                return "video/webm"

        return "video/mp4"

    def _cleanup_expired(self):
        """清理过期的视频"""
        expired_ids = [
            vid for vid, video in self._cache.items()
            if video.is_expired()
        ]
        for vid in expired_ids:
            self._cleanup_video(vid)
            self._cache.pop(vid, None)


# 全局视频暂存管理器
_video_store: Optional[VideoStore] = None


def get_video_store() -> VideoStore:
    """获取全局视频暂存管理器"""
    global _video_store
    if _video_store is None:
        _video_store = VideoStore()
    return _video_store


# ========== 视频分块传输 ==========

class VideoChunkTransferParams(ToolParameters):
    """视频分块传输参数"""
    selector: str = Field(
        ...,
        description="文件输入框的 CSS 选择器"
    )
    tab_id: Optional[int] = Field(
        None,
        description="标签页 ID"
    )
    clear_after_set: bool = Field(
        False,
        description="设置后是否清除暂存视频"
    )
    timeout: Optional[int] = Field(
        60000,
        description="超时时间（毫秒）"
    )


class VideoChunkTransferResult:
    """视频分块传输结果"""
    success: bool
    file_name: str
    file_size: int
    chunks: int
    message: str
    need_upload: bool = False

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "chunks": self.chunks,
            "message": self.message,
            "need_upload": self.need_upload
        }


@tool(
    name="xhs_video_transfer",
    description="将暂存的视频分块传输到页面并设置到文件输入框",
    category="browser",
    version="1.0.0",
    tags=["xhs", "xiaohongshu", "video", "upload", "chunk"]
)
class VideoChunkTransferTool(Tool[VideoChunkTransferParams, VideoChunkTransferResult]):
    """视频分块传输工具"""

    CHUNK_SIZE = 20 * 1024 * 1024  # 20MB

    async def execute(
        self,
        params: VideoChunkTransferParams,
        context: ExecutionContext
    ) -> Result[VideoChunkTransferResult]:
        """执行视频分块传输"""
        try:
            # 获取暂存的视频
            store = get_video_store()
            stored_video = store.get()

            if not stored_video:
                return self.ok(VideoChunkTransferResult(
                    success=False,
                    file_name="",
                    file_size=0,
                    chunks=0,
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

            # 传输视频
            result = await self._transfer_video(
                stored_video=stored_video,
                selector=params.selector,
                tab_id=tab_id,
                timeout=params.timeout
            )

            # 如果需要清除暂存
            if params.clear_after_set and result.success:
                store.clear(stored_video.video_id)

            return self.ok(result)

        except Exception as e:
            return self.error_from_exception(e)

    async def _transfer_video(
        self,
        stored_video: StoredVideo,
        selector: str,
        tab_id: int,
        timeout: int
    ) -> VideoChunkTransferResult:
        """执行分块传输"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            # 计算分块数
            total_chunks = (stored_video.file_size + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE

            # 1. 初始化视频接收器
            init_result = await self._init_video_receiver(
                client=client,
                tab_id=tab_id,
                total_chunks=total_chunks,
                file_name=stored_video.file_name,
                file_type=stored_video.file_type,
                timeout=10000
            )

            if not init_result:
                return VideoChunkTransferResult(
                    success=False,
                    file_name=stored_video.file_name,
                    file_size=stored_video.file_size,
                    chunks=0,
                    message="初始化视频接收器超时"
                )

            # 2. 分块传输
            for i in range(total_chunks):
                start = i * self.CHUNK_SIZE
                end = min(start + self.CHUNK_SIZE, stored_video.file_size)
                chunk_data = stored_video.data[start:end]

                # 转换为 Base64
                base64_data = base64.b64encode(chunk_data).decode('ascii')
                progress = round((i + 1) / total_chunks * 100)

                # 显示进度
                await self._show_progress(
                    client=client,
                    tab_id=tab_id,
                    progress=progress,
                    current=i + 1,
                    total=total_chunks
                )

                # 发送分块
                chunk_sent = await self._send_chunk(
                    client=client,
                    tab_id=tab_id,
                    chunk_index=i,
                    chunk_data=base64_data,
                    timeout=30000
                )

                if not chunk_sent:
                    return VideoChunkTransferResult(
                        success=False,
                        file_name=stored_video.file_name,
                        file_size=stored_video.file_size,
                        chunks=i,
                        message=f"发送分块 {i + 1} 超时"
                    )

            # 3. 设置视频到 input
            set_result = await self._set_video_to_input(
                client=client,
                tab_id=tab_id,
                selector=selector,
                timeout=30000
            )

            if not set_result.success:
                return VideoChunkTransferResult(
                    success=False,
                    file_name=stored_video.file_name,
                    file_size=stored_video.file_size,
                    chunks=total_chunks,
                    message=set_result.message or "设置视频到 file input 失败"
                )

            return VideoChunkTransferResult(
                success=True,
                file_name=stored_video.file_name,
                file_size=stored_video.file_size,
                chunks=total_chunks,
                message="视频分块传输成功"
            )

        except Exception as e:
            return VideoChunkTransferResult(
                success=False,
                file_name=stored_video.file_name,
                file_size=stored_video.file_size,
                chunks=0,
                message=f"传输失败: {str(e)}"
            )

    async def _init_video_receiver(
        self,
        client,
        tab_id: int,
        total_chunks: int,
        file_name: str,
        file_type: str,
        timeout: int
    ) -> bool:
        """初始化视频接收器"""
        try:
            await asyncio.wait_for(
                client.call_tool(
                    "inject_script",
                    code=self._create_init_receiver_code(total_chunks, file_name, file_type),
                    world="MAIN"
                ),
                timeout=timeout / 1000
            )
            return True
        except Exception:
            return False

    def _create_init_receiver_code(
        self,
        total_chunks: int,
        file_name: str,
        file_type: str
    ) -> str:
        """创建初始化接收器的 JavaScript 代码"""
        return f"""
        (function() {{
            window.__xhsVideoReceiver = {{
                chunks: new Array({total_chunks}),
                receivedChunks: 0,
                totalChunks: {total_chunks},
                fileName: "{file_name}",
                fileType: "{file_type}",
                data: null
            }};
            "初始化视频接收器成功，共 {total_chunks} 个分块";
        }})()
        """

    async def _send_chunk(
        self,
        client,
        tab_id: int,
        chunk_index: int,
        chunk_data: str,
        timeout: int
    ) -> bool:
        """发送分块"""
        try:
            await asyncio.wait_for(
                client.call_tool(
                    "inject_script",
                    code=self._create_chunk_code(chunk_index, chunk_data),
                    world="MAIN"
                ),
                timeout=timeout / 1000
            )
            return True
        except Exception:
            return False

    def _create_chunk_code(self, chunk_index: int, chunk_data: str) -> str:
        """创建发送分块的 JavaScript 代码"""
        return f"""
        (function() {{
            const receiver = window.__xhsVideoReceiver;
            if (receiver) {{
                try {{
                    // 解码 Base64
                    const binaryString = atob("{chunk_data}");
                    const len = binaryString.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {{
                        bytes[i] = binaryString.charCodeAt(i);
                    }}

                    // 存储分块
                    receiver.chunks[{chunk_index}] = bytes;
                    receiver.receivedChunks++;

                    // 检查是否完成
                    if (receiver.receivedChunks === receiver.totalChunks) {{
                        // 合并所有分块
                        let totalLength = 0;
                        for (let i = 0; i < receiver.chunks.length; i++) {{
                            totalLength += receiver.chunks[i].length;
                        }}
                        const combined = new Uint8Array(totalLength);
                        let offset = 0;
                        for (let i = 0; i < receiver.chunks.length; i++) {{
                            combined.set(receiver.chunks[i], offset);
                            offset += receiver.chunks[i].length;
                        }}
                        receiver.data = combined;
                        "分块合并完成";
                    }}

                    return true;
                }} catch (e) {{
                    return {{ error: {{ message: e.message }} }};
                }}
            }}
            return {{ error: {{ message: "接收器未初始化" }} }};
        }})()
        """

    async def _set_video_to_input(
        self,
        client,
        tab_id: int,
        selector: str,
        timeout: int
    ) -> VideoChunkTransferResult:
        """设置视频到文件输入框"""
        try:
            result = await asyncio.wait_for(
                client.call_tool(
                    "inject_script",
                    code=self._create_set_input_code(selector),
                    world="MAIN"
                ),
                timeout=timeout / 1000
            )

            # 解析结果
            if isinstance(result, dict):
                if result.get("isError"):
                    return VideoChunkTransferResult(
                        success=False,
                        file_name="",
                        file_size=0,
                        chunks=0,
                        message=result.get("content", [{}])[0].get("text", "设置失败")
                    )
                else:
                    return VideoChunkTransferResult(
                        success=True,
                        file_name="",
                        file_size=0,
                        chunks=0,
                        message="设置成功"
                    )

            return VideoChunkTransferResult(
                success=True,
                file_name="",
                file_size=0,
                chunks=0,
                message="设置完成"
            )

        except Exception as e:
            return VideoChunkTransferResult(
                success=False,
                file_name="",
                file_size=0,
                chunks=0,
                message=f"设置超时: {str(e)}"
            )

    def _create_set_input_code(self, selector: str) -> str:
        """创建设置文件输入框的 JavaScript 代码"""
        return f"""
        (function() {{
            try {{
                const input = document.querySelector('{selector}');
                if (!input) {{
                    return {{ error: {{ message: "文件输入框未找到: {selector}" }} }};
                }}

                if (!(input instanceof HTMLInputElement) || input.type !== 'file') {{
                    return {{ error: {{ message: "选择器指向的不是文件输入框" }} }};
                }}

                const receiver = window.__xhsVideoReceiver;
                if (!receiver || !receiver.data) {{
                    return {{ error: {{ message: "视频数据未准备好" }} }};
                }}

                // 创建 File 对象
                const blob = new Blob([receiver.data], {{ type: receiver.fileType }});
                const file = new File([blob], receiver.fileName, {{ type: receiver.fileType }});

                // 使用 DataTransfer 设置文件
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                input.files = dataTransfer.files;

                // 触发事件
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));

                return {{
                    success: true,
                    fileName: receiver.fileName,
                    fileSize: receiver.data.length,
                    chunks: receiver.totalChunks
                }};
            }} catch (e) {{
                return {{ error: {{ message: e.message }} }};
            }}
        }})()
        """

    async def _show_progress(
        self,
        client,
        tab_id: int,
        progress: int,
        current: int,
        total: int
    ):
        """显示进度"""
        try:
            await client.call_tool(
                "inject_script",
                code=f"""
                (function() {{
                    if (typeof window.__showToast === 'function') {{
                        window.__showToast(`正在组装视频... {progress}% ({current}/{total})`);
                    }}
                }})()
                """,
                world="MAIN"
            )
        except Exception:
            pass


# ========== 便捷函数 ==========

async def transfer_video_to_page(
    selector: str,
    tab_id: Optional[int] = None,
    clear_after_set: bool = False,
    timeout: int = 60000,
    context: ExecutionContext = None
) -> Result[VideoChunkTransferResult]:
    """将视频分块传输到页面"""
    params = VideoChunkTransferParams(
        selector=selector,
        tab_id=tab_id,
        clear_after_set=clear_after_set,
        timeout=timeout
    )
    tool = VideoChunkTransferTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = [
    # 视频暂存管理
    "VideoStore",
    "StoredVideo",
    "get_video_store",
    # 视频分块传输
    "VideoChunkTransferTool",
    "VideoChunkTransferParams",
    "VideoChunkTransferResult",
    "transfer_video_to_page",
]
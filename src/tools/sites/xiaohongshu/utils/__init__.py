"""
小红书工具模块

提供小红书 RPA 所需的底层工具实现。
"""

from .video_transfer import (
    VideoStore,
    StoredVideo,
    get_video_store,
    VideoChunkTransferTool,
    VideoChunkTransferParams,
    VideoChunkTransferResult,
    transfer_video_to_page,
)

from .video_download import (
    VideoDownloadTool,
    VideoDownloadParams,
    VideoDownloadResult,
    download_video,
)

from .video_intercept import (
    VideoUploadInterceptTool,
    VideoUploadInterceptParams,
    VideoUploadInterceptResult,
    intercept_upload,
)

from .file_upload import (
    FileData,
    UploadFileTool,
    UploadFileParams,
    UploadFileResult,
    upload_file,
    SetFilesTool,
    SetFilesParams,
    SetFilesResult,
    set_files,
)

from .inject_script import (
    InjectScriptTool,
    InjectScriptParams,
    inject_script,
)

from .page_data import (
    ReadPageDataTool,
    ReadPageDataParams,
    ReadPageDataResult,
    read_page_data,
)

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
    # 视频下载
    "VideoDownloadTool",
    "VideoDownloadParams",
    "VideoDownloadResult",
    "download_video",
    # 视频上传拦截
    "VideoUploadInterceptTool",
    "VideoUploadInterceptParams",
    "VideoUploadInterceptResult",
    "intercept_upload",
    # 文件上传
    "FileData",
    "UploadFileTool",
    "UploadFileParams",
    "UploadFileResult",
    "upload_file",
    "SetFilesTool",
    "SetFilesParams",
    "SetFilesResult",
    "set_files",
    # 脚本注入
    "InjectScriptTool",
    "InjectScriptParams",
    "inject_script",
    # 页面数据读取
    "ReadPageDataTool",
    "ReadPageDataParams",
    "ReadPageDataResult",
    "read_page_data",
]
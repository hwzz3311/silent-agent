"""
文件上传工具

提供将 Base64 编码的文件设置到文件输入框的功能。

整合迁移自:
- src/tools/xhs/upload_file.py (UploadFileTool)
- src/tools/xhs/set_files.py (SetFilesTool)
"""

import json
from typing import Optional, List, Dict, Any
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


# ========== 共享数据类 ==========

class FileData(ToolParameters):
    """文件数据（用于多文件上传）"""
    base64_data: str = Field(
        ...,
        description="Base64 编码的文件内容"
    )
    file_name: str = Field(
        ...,
        description="文件名"
    )
    mime_type: str = Field(
        ...,
        description="MIME 类型"
    )


# ========== 单文件上传 ==========

class UploadFileParams(ToolParameters):
    """单文件上传参数"""
    selector: str = Field(
        ...,
        description="文件输入框的 CSS 选择器"
    )
    base64_data: str = Field(
        ...,
        description="Base64 编码的文件内容"
    )
    file_name: str = Field(
        "file",
        description="文件名"
    )
    mime_type: str = Field(
        "application/octet-stream",
        description="MIME 类型"
    )
    timeout: Optional[int] = Field(
        30000,
        description="超时时间（毫秒）"
    )


class UploadFileResult:
    """单文件上传结果"""
    success: bool
    selector: str
    file_name: str
    mime_type: str
    message: str

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "selector": self.selector,
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "message": self.message
        }


@tool(
    name="xhs_upload_file",
    description="将 Base64 编码的文件设置到文件输入框（单文件）",
    category="browser",
    version="1.0.0",
    tags=["xhs", "xiaohongshu", "upload", "file", "base64"]
)
class UploadFileTool(Tool[UploadFileParams, UploadFileResult]):
    """单文件上传工具"""

    async def execute(
        self,
        params: UploadFileParams,
        context: ExecutionContext
    ) -> Result[UploadFileResult]:
        """执行文件上传"""
        try:
            from src.relay_client import SilentAgentClient

            client = SilentAgentClient()

            # 构建注入代码
            inject_code = self._create_upload_code(
                selector=params.selector,
                base64_data=params.base64_data,
                file_name=params.file_name,
                mime_type=params.mime_type
            )

            # 执行注入
            raw_result = await client.call_tool(
                "inject_script",
                code=inject_code,
                world="MAIN"
            )

            # 解析结果
            if isinstance(raw_result, dict):
                if raw_result.get("isError"):
                    error_text = raw_result.get("content", [{}])[0].get("text", "上传失败")
                    return self.fail(error_text)
                else:
                    return self.ok(UploadFileResult(
                        success=True,
                        selector=params.selector,
                        file_name=params.file_name,
                        mime_type=params.mime_type,
                        message="文件上传成功"
                    ))
            else:
                return self.ok(UploadFileResult(
                    success=True,
                    selector=params.selector,
                    file_name=params.file_name,
                    mime_type=params.mime_type,
                    message="文件上传成功"
                ))

        except Exception as e:
            return self.error_from_exception(e)

    def _create_upload_code(
        self,
        selector: str,
        base64_data: str,
        file_name: str,
        mime_type: str
    ) -> str:
        """创建上传文件的 JavaScript 代码"""
        return f"""
        (function() {{
            try {{
                // 查找文件输入框
                const input = document.querySelector('{selector}');
                if (!input) {{
                    return {{ error: {{ message: "文件输入框未找到: {selector}" }} }};
                }}

                // 验证是文件输入框
                if (!(input instanceof HTMLInputElement) || input.type !== 'file') {{
                    return {{ error: {{ message: "选择器指向的不是文件输入框" }} }};
                }}

                // 解码 Base64
                const base64 = "{base64_data}";
                const binaryString = atob(base64.replace(/^data:[^;]+;base64,/, ''));
                const len = binaryString.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {{
                    bytes[i] = binaryString.charCodeAt(i);
                }}

                // 创建 Blob 和 File
                const blob = new Blob([bytes], {{ type: "{mime_type}" }});
                const file = new File([blob], "{file_name}", {{ type: "{mime_type}" }});

                // 使用 DataTransfer 设置文件
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                input.files = dataTransfer.files;

                // 触发事件
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));

                return {{
                    success: true,
                    fileName: "{file_name}",
                    mimeType: "{mime_type}",
                    message: "文件上传成功"
                }};
            }} catch (e) {{
                return {{ error: {{ message: e.message }} }};
            }}
        }})()
        """


# ========== 多文件上传 ==========

class SetFilesParams(ToolParameters):
    """多文件设置参数"""
    selector: str = Field(
        ...,
        description="文件输入框的 CSS 选择器"
    )
    files: List[FileData] = Field(
        ...,
        description="文件数据列表"
    )
    timeout: Optional[int] = Field(
        30000,
        description="超时时间（毫秒）"
    )


class SetFilesResult:
    """多文件设置结果"""
    success: bool
    selector: str
    file_count: int
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "selector": self.selector,
            "file_count": self.file_count,
            "message": self.message
        }


@tool(
    name="xhs_set_files",
    description="将多个文件设置到文件输入框",
    category="browser",
    version="1.0.0",
    tags=["xhs", "xiaohongshu", "upload", "files", "multiple"]
)
class SetFilesTool(Tool[SetFilesParams, SetFilesResult]):
    """多文件设置工具"""

    async def execute(
        self,
        params: SetFilesParams,
        context: ExecutionContext
    ) -> Result[SetFilesResult]:
        """执行多文件设置"""
        try:
            from src.relay_client import SilentAgentClient

            client = SilentAgentClient()

            # 构建注入代码
            # Pydantic v2+ uses model_dump, v1 uses dict
            def dump_file(f):
                if hasattr(f, 'model_dump'):
                    return f.model_dump()
                else:
                    return f.dict()

            inject_code = self._create_set_files_code(
                selector=params.selector,
                files=[dump_file(f) for f in params.files]
            )

            # 执行注入
            raw_result = await client.call_tool(
                "inject_script",
                code=inject_code,
                world="MAIN"
            )

            # 解析结果
            if isinstance(raw_result, dict):
                if raw_result.get("isError"):
                    error_text = raw_result.get("content", [{}])[0].get("text", "设置失败")
                    return self.fail(error_text)
                else:
                    return self.ok(SetFilesResult(
                        success=True,
                        selector=params.selector,
                        file_count=len(params.files),
                        message="文件设置成功"
                    ))
            else:
                return self.ok(SetFilesResult(
                    success=True,
                    selector=params.selector,
                    file_count=len(params.files),
                    message="文件设置成功"
                ))

        except Exception as e:
            return self.error_from_exception(e)

    def _create_set_files_code(
        self,
        selector: str,
        files: List[Dict[str, str]]
    ) -> str:
        """创建设置多个文件的 JavaScript 代码"""
        files_json = json.dumps(files)

        return f"""
        (function() {{
            try {{
                // 查找文件输入框
                const input = document.querySelector('{selector}');
                if (!input) {{
                    return {{ error: {{ message: "文件输入框未找到: {selector}" }} }};
                }}

                // 验证是文件输入框
                if (!(input instanceof HTMLInputElement) || input.type !== 'file') {{
                    return {{ error: {{ message: "选择器指向的不是文件输入框" }} }};
                }}

                // 解析文件数据
                const filesData = {files_json};

                // 处理每个文件
                const dataTransfer = new DataTransfer();
                for (const fileData of filesData) {{
                    // 解码 Base64
                    const base64 = fileData.base64Data.replace(/^data:[^;]+;base64,/, '');
                    const binaryString = atob(base64);
                    const len = binaryString.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {{
                        bytes[i] = binaryString.charCodeAt(i);
                    }}

                    // 创建 Blob 和 File
                    const blob = new Blob([bytes], {{ type: fileData.mimeType }});
                    const file = new File([blob], fileData.fileName, {{ type: fileData.mimeType }});

                    // 添加到 DataTransfer
                    dataTransfer.items.add(file);
                }}

                // 设置文件到 input
                input.files = dataTransfer.files;

                // 触发事件
                input.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));
                input.dispatchEvent(new Event('input', {{ bubbles: true, cancelable: true }}));

                return {{
                    success: true,
                    selector: '{selector}',
                    fileCount: filesData.length,
                    message: '文件设置成功'
                }};
            }} catch (e) {{
                return {{ error: {{ message: e.message }} }};
            }}
        }})()
        """


# ========== 便捷函数 ==========

async def upload_file(
    selector: str,
    base64_data: str,
    file_name: str = "file",
    mime_type: str = "application/octet-stream",
    timeout: int = 30000,
    context: ExecutionContext = None
) -> Result[UploadFileResult]:
    """上传单个文件"""
    params = UploadFileParams(
        selector=selector,
        base64_data=base64_data,
        file_name=file_name,
        mime_type=mime_type,
        timeout=timeout
    )
    tool = UploadFileTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


async def set_files(
    selector: str,
    files: List[Dict[str, str]],
    timeout: int = 30000,
    context: ExecutionContext = None
) -> Result[SetFilesResult]:
    """设置多个文件到文件输入框"""
    file_data_list = [FileData(**f) for f in files]
    params = SetFilesParams(
        selector=selector,
        files=file_data_list,
        timeout=timeout
    )
    tool = SetFilesTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = [
    # 共享数据类
    "FileData",
    # 单文件上传
    "UploadFileTool",
    "UploadFileParams",
    "UploadFileResult",
    "upload_file",
    # 多文件上传
    "SetFilesTool",
    "SetFilesParams",
    "SetFilesResult",
    "set_files",
]
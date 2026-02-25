"""
页面数据读取工具

读取小红书页面 window/document 属性数据，支持 dotted path 解析和循环引用处理。

迁移自: src/tools/xhs/xhs_read_page_data.py
"""

import json
from typing import Optional, Any
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result, Error


class ReadPageDataParams(ToolParameters):
    """页面数据读取参数"""
    path: str = Field(
        ...,
        description="属性路径，支持点分语法，如 'location.href', '__INITIAL_STATE__.user.id'"
    )
    tab_id: Optional[int] = Field(
        None,
        description="标签页 ID，默认使用当前活动标签页"
    )


class ReadPageDataResult:
    """读取页面数据结果"""

    def __init__(self, path: str, value: Any, type: str, success: bool = True):
        self.path = path
        self.value = value
        self.type = type
        self.success = success

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "value": self.value,
            "type": self.type,
            "success": self.success
        }


@tool(
    name="xhs_read_page_data",
    description="读取小红书页面 window/document 属性数据，支持 dotted path 解析",
    category="browser",
    version="1.0.0",
    tags=["xhs", "xiaohongshu", "page", "data", "read"]
)
class ReadPageDataTool(Tool[ReadPageDataParams, ReadPageDataResult]):
    """页面数据读取工具"""

    async def execute(
        self,
        params: ReadPageDataParams,
        context: ExecutionContext
    ) -> Result[ReadPageDataResult]:
        """执行页面数据读取"""
        try:
            # 构建读取页面数据的 JavaScript 代码
            read_code = self._build_read_code(params.path)

            # 执行代码
            world = context.world or "MAIN"
            eval_result = await self._execute_read_script(
                code=read_code,
                world=world,
                tab_id=params.tab_id
            )

            if eval_result.success:
                value = eval_result.data
                result = ReadPageDataResult(
                    path=params.path,
                    value=value,
                    type=self._get_type(value)
                )
                return self.ok(result)
            else:
                return self.fail(
                    message=f"读取页面数据失败: {eval_result.error}",
                    details={"path": params.path}
                )

        except Exception as e:
            return self.error_from_exception(e)

    def _build_read_code(self, path: str) -> str:
        """构建读取页面数据的 JavaScript 代码"""
        # 处理 dotted path
        keys = path.split(".")

        if len(keys) == 1:
            # 简单情况：直接读取 window 属性
            return f"""
            (function() {{
                const path = "{path}";
                let value = window[path];

                // 处理循环引用和函数
                try {{
                    const json = JSON.stringify(value);
                    return JSON.parse(json);
                }} catch (e) {{
                    return String(value);
                }}
            }})()
            """
        else:
            # 嵌套路径，如 __INITIAL_STATE__.user.id
            window_access = "window"
            for key in keys:
                window_access = f"({window_access}['{key}'] || {window_access}.{key})"

            return f"""
            (function() {{
                const keys = {keys};
                let value = window;
                for (const key of keys) {{
                    if (key && value != null) {{
                        value = value[key] || value[key.replace(/-/g, '_')];
                    }} else {{
                        return undefined;
                    }}
                }}

                // 处理循环引用和函数
                try {{
                    const json = JSON.stringify(value);
                    return JSON.parse(json);
                }} catch (e) {{
                    return String(value);
                }}
            }})()
            """

    async def _execute_read_script(
        self,
        code: str,
        world: str,
        tab_id: Optional[int] = None
    ) -> Result[Any]:
        """执行读取脚本"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            raw_result = await client.call_tool(
                "inject_script",
                code=code,
                world=world,
            )

            # 解析结果
            if isinstance(raw_result, dict):
                if raw_result.get("content"):
                    content = raw_result["content"]
                    is_error = raw_result.get("isError", False)
                    if is_error:
                        error_text = content[0].get("text", "脚本执行失败")
                        return Result.fail(
                            Error(
                                code="EXECUTION_FAILED",
                                message=error_text
                            )
                        )
                    else:
                        try:
                            data = content[0].get("text", "")
                            if data:
                                parsed = json.loads(data)
                                return Result.ok(parsed)
                        except (json.JSONDecodeError, IndexError):
                            return Result.ok(content[0].get("text") if content else None)
                else:
                    return Result.ok(raw_result)
            else:
                return Result.ok(raw_result)

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    def _get_type(self, value: Any) -> str:
        """获取值类型"""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "unknown"


# ========== 便捷函数 ==========

async def read_page_data(
    path: str,
    tab_id: Optional[int] = None,
    context: ExecutionContext = None
) -> Result[ReadPageDataResult]:
    """读取小红书页面数据"""
    params = ReadPageDataParams(path=path, tab_id=tab_id)
    tool = ReadPageDataTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = [
    "ReadPageDataTool",
    "ReadPageDataParams",
    "ReadPageDataResult",
    "read_page_data",
]
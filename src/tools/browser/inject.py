"""
注入工具

提供在页面中执行 JavaScript 的功能。
"""

from typing import Literal, Optional
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class InjectParams(ToolParameters):
    """注入参数"""
    code: str = Field(..., description="要执行的 JavaScript 代码")
    world: Literal["MAIN", "ISOLATED"] = Field(
        "MAIN", description="执行世界: MAIN=页面上下文, ISOLATED=隔离世界"
    )


@tool(name="browser.inject", description="在页面中执行 JavaScript")
class InjectTool(Tool[InjectParams, any]):
    """注入工具"""

    async def execute(
        self,
        params: InjectParams,
        context: ExecutionContext
    ) -> Result[any]:
        """执行注入"""
        from src.relay_client import NeuroneClient

        client = NeuroneClient()

        try:
            raw_result = await client.call_tool(
                "inject_script",
                code=params.code,
                world=params.world,
            )

            if isinstance(raw_result, dict):
                if raw_result.get("content"):
                    content = raw_result["content"]
                    is_error = raw_result.get("isError", False)
                    if is_error:
                        error_text = content[0].get("text", "脚本执行失败") if content else "脚本执行失败"
                        return self.fail(error_text)
                    else:
                        # 解析内容
                        try:
                            data = content[0].get("text", "")
                            if data:
                                import json
                                parsed = json.loads(data)
                                return self.ok(parsed)
                        except (json.JSONDecodeError, IndexError):
                            return self.ok(content[0].get("text") if content else None)
                else:
                    return self.ok(raw_result)
            else:
                return self.ok(raw_result)

        except Exception as e:
            return self.error_from_exception(e)


# 便捷函数
async def inject(
    code: str,
    world: str = "MAIN",
    context: ExecutionContext = None
) -> Result[any]:
    """在页面中执行 JavaScript"""
    params = InjectParams(code=code, world=world)  # type: ignore
    tool = InjectTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["InjectTool", "InjectParams", "inject"]
"""
提取工具

提供从页面提取数据的功能。
"""

from typing import Optional, Literal
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class ExtractParams(ToolParameters):
    """提取参数"""
    selector: Optional[str] = Field(None, description="CSS 选择器")
    path: Optional[str] = Field(None, description="Window 对象路径 (e.g., 'location.href')")
    attribute: str = Field("text", description="提取属性: text, html, value, href 等")
    source: Literal["element", "window", "document"] = Field(
        "element", description="数据来源"
    )
    all: bool = Field(False, description="是否提取所有匹配元素")


@tool(name="browser.extract", description="从页面提取数据")
class ExtractTool(Tool[ExtractParams, any]):
    """提取工具"""

    async def execute(
        self,
        params: ExtractParams,
        context: ExecutionContext
    ) -> Result[any]:
        """执行提取"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            raw_result = await client.call_tool(
                "chrome_extract_data",
                selector=params.selector,
                path=params.path,
                attribute=params.attribute,
                source=params.source,
                all=params.all,
            )

            if isinstance(raw_result, dict):
                if raw_result.get("content"):
                    content = raw_result["content"]
                    is_error = raw_result.get("isError", False)
                    if is_error:
                        error_text = content[0].get("text", "提取失败") if content else "提取失败"
                        return self.fail(error_text)
                    else:
                        data = content[0].get("text", "")
                        # 尝试解析 JSON
                        try:
                            import json
                            return self.ok(json.loads(data))
                        except (json.JSONDecodeError, IndexError):
                            return self.ok(content[0].get("text") if content else None)
                else:
                    return self.ok(raw_result)
            else:
                return self.ok(raw_result)

        except Exception as e:
            return self.error_from_exception(e)


# 便捷函数
async def extract(
    selector: str = None,
    path: str = None,
    attribute: str = "text",
    source: str = "element",
    all: bool = False,
    context: ExecutionContext = None
) -> Result[any]:
    """从页面提取数据"""
    params = ExtractParams(
        selector=selector,
        path=path,
        attribute=attribute,
        source=source,  # type: ignore
        all=all,
    )
    tool = ExtractTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


# 便捷函数：读取 window 属性
async def read_window(path: str, context: ExecutionContext = None) -> Result[any]:
    """读取 window 对象属性"""
    return await extract(selector=None, path=path, source="window")


__all__ = ["ExtractTool", "ExtractParams", "extract", "read_window"]
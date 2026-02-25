"""
滚动工具

提供页面滚动功能。
"""

from typing import Optional, Literal
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class ScrollParams(ToolParameters):
    """滚动参数"""
    selector: Optional[str] = Field(None, description="元素选择器（指定元素则滚动该元素）")
    direction: Literal["up", "down", "left", "right", "top", "bottom"] = Field(
        "down", description="滚动方向"
    )
    amount: int = Field(300, ge=0, description="滚动距离（像素）")


@tool(name="browser.scroll", description="滚动页面或元素")
class ScrollTool(Tool[ScrollParams, dict]):
    """滚动工具"""

    async def execute(
        self,
        params: ScrollParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行滚动"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            raw_result = await client.call_tool(
                "chrome_scroll",
                selector=params.selector,
                direction=params.direction,
                amount=params.amount,
            )

            return self.ok({"success": True, "direction": params.direction})

        except Exception as e:
            return self.error_from_exception(e, recoverable=True)


# 便捷函数
async def scroll(
    direction: str = "down",
    amount: int = 300,
    selector: str = None,
    context: ExecutionContext = None
) -> Result[dict]:
    """滚动页面"""
    params = ScrollParams(
        selector=selector,
        direction=direction,  # type: ignore
        amount=amount,
    )
    tool = ScrollTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["ScrollTool", "ScrollParams", "scroll"]
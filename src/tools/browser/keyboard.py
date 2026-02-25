"""
键盘工具

提供模拟键盘输入的功能。
"""

from typing import Optional
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class KeyboardParams(ToolParameters):
    """键盘参数"""
    keys: str = Field(..., description="按键列表，逗号分隔 (如 'Enter,Tab,a,b')")
    selector: Optional[str] = Field(None, description="目标元素选择器")
    delay: int = Field(50, ge=0, description="按键间隔（毫秒）")


@tool(name="browser.keyboard", description="模拟键盘输入")
class KeyboardTool(Tool[KeyboardParams, dict]):
    """键盘工具"""

    async def execute(
        self,
        params: KeyboardParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行键盘输入"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            raw_result = await client.call_tool(
                "chrome_keyboard",
                keys=params.keys,
                selector=params.selector,
                delay=params.delay,
            )

            return self.ok({
                "success": True,
                "keys_pressed": len(params.keys.split(",")),
            })

        except Exception as e:
            return self.error_from_exception(e, recoverable=True)


# 便捷函数
async def keyboard(
    keys: str,
    selector: str = None,
    delay: int = 50,
    context: ExecutionContext = None
) -> Result[dict]:
    """模拟键盘输入"""
    params = KeyboardParams(keys=keys, selector=selector, delay=delay)
    tool = KeyboardTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["KeyboardTool", "KeyboardParams", "keyboard"]
"""
填充工具

提供填充表单输入框的功能。
"""

from typing import Literal
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class FillParams(ToolParameters):
    """填充参数"""
    selector: str = Field(..., description="CSS 选择器")
    value: str = Field(..., description="要填充的值")
    method: Literal["set", "type", "execCommand"] = Field(
        "set", description="填充方法: set=直接设置, type=模拟打字, execCommand=execCommand"
    )
    clear_before: bool = Field(True, description="填充前是否清空")
    timeout: int = Field(5000, ge=0, le=60000, description="超时时间（毫秒）")


@tool(name="browser.fill", description="填充表单输入框")
class FillTool(Tool[FillParams, dict]):
    """填充工具"""

    async def execute(
        self,
        params: FillParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行填充"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            raw_result = await client.call_tool(
                "chrome_fill",
                selector=params.selector,
                value=params.value,
                method=params.method,
                clearBefore=params.clear_before,
                timeout=params.timeout,
            )

            if isinstance(raw_result, dict):
                if raw_result.get("content"):
                    content = raw_result["content"]
                    is_error = raw_result.get("isError", False)
                    if is_error:
                        error_text = content[0].get("text", "填充失败") if content else "填充失败"
                        return self.fail(error_text, recoverable=True, details={"selector": params.selector})
                    else:
                        return self.ok({"success": True, "selector": params.selector, "method": params.method})
                else:
                    return self.ok({"success": True, "selector": params.selector, "value": params.value, **raw_result})
            else:
                return self.ok({"success": True, "selector": params.selector, "value": params.value})

        except Exception as e:
            return self.error_from_exception(e, recoverable=True)


# 便捷函数
async def fill(
    selector: str,
    value: str,
    method: str = "set",
    clear_before: bool = True,
    timeout: int = 5000,
    context: ExecutionContext = None
) -> Result[dict]:
    """填充表单"""
    params = FillParams(
        selector=selector,
        value=value,
        method=method,  # type: ignore
        clear_before=clear_before,
        timeout=timeout,
    )
    tool = FillTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["FillTool", "FillParams", "fill"]
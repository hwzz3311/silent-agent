"""
等待工具

提供等待元素出现或等待条件的功能。
"""

from typing import Optional
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class WaitParams(ToolParameters):
    """等待参数"""
    selector: Optional[str] = Field(None, description="元素选择器")
    count: int = Field(1, ge=0, description="期望的元素数量")
    timeout: int = Field(60000, ge=0, le=300000, description="超时时间（毫秒）")
    check_interval: int = Field(500, ge=100, description="检查间隔（毫秒）")


@tool(name="browser.wait", description="等待元素出现或条件满足")
class WaitTool(Tool[WaitParams, dict]):
    """等待工具"""

    async def execute(
        self,
        params: WaitParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行等待"""
        from src.relay_client import NeuroneClient

        client = NeuroneClient()

        try:
            raw_result = await client.call_tool(
                "chrome_wait_elements",
                selector=params.selector or "",
                count=params.count,
                timeout=params.timeout,
                checkInterval=params.check_interval,
            )

            if isinstance(raw_result, dict):
                if raw_result.get("success"):
                    return self.ok({
                        "success": True,
                        "found": raw_result.get("found"),
                        "expected": params.count,
                    })
                else:
                    return self.fail(
                        f"等待超时: 期望 {params.count} 个元素，找到 {raw_result.get('found', 0)}",
                        recoverable=True,
                        details={
                            "selector": params.selector,
                            "expected": params.count,
                            "found": raw_result.get("found"),
                        }
                    )
            else:
                return self.fail("等待返回格式错误")

        except Exception as e:
            return self.error_from_exception(e, recoverable=True)


# 便捷函数
async def wait(
    selector: str = None,
    count: int = 1,
    timeout: int = 60000,
    check_interval: int = 500,
    context: ExecutionContext = None
) -> Result[dict]:
    """等待元素"""
    params = WaitParams(
        selector=selector,
        count=count,
        timeout=timeout,
        check_interval=check_interval,
    )
    tool = WaitTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["WaitTool", "WaitParams", "wait"]
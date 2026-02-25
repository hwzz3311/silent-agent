"""
点击工具

提供点击页面元素的功能。
"""

from typing import Optional, Literal
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result, ResultMeta


class ClickParams(ToolParameters):
    """点击参数"""
    selector: str = Field(..., description="CSS 选择器")
    text: Optional[str] = Field(None, description="元素文本内容（用于精确定位）")
    button: Literal["left", "middle", "right"] = Field("left", description="鼠标按钮")
    count: int = Field(1, ge=1, le=5, description="点击次数")
    timeout: int = Field(5000, ge=0, le=60000, description="等待元素超时（毫秒）")
    force: bool = Field(False, description="是否强制点击（即使元素被认为不可点击）")
    scroll_into_view: bool = Field(True, description="是否滚动到可见区域")
    wait_for_navigation: bool = Field(False, description="是否等待导航完成")


@tool(name="browser.click", description="点击页面上的元素")
class ClickTool(Tool[ClickParams, dict]):
    """点击工具"""

    async def execute(
        self,
        params: ClickParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行点击"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            # 调用扩展的 click 工具
            raw_result = await client.call_tool(
                "chrome_click",
                selector=params.selector,
                text=params.text,
                timeout=params.timeout,
                waitForNav=params.wait_for_navigation,
            )

            # SilentAgentClient 返回的是原始结果 (dict)，需要转换为 Result
            if isinstance(raw_result, dict):
                if raw_result.get("content"):
                    # 工具返回格式: {content: [{type: 'text' | 'error', text: ...}]}
                    content = raw_result["content"]
                    is_error = raw_result.get("isError", False)
                    if is_error:
                        error_text = content[0].get("text", "点击失败") if content else "点击失败"
                        return self.fail(error_text, recoverable=True, details={"selector": params.selector})
                    else:
                        return self.ok({"success": True, "selector": params.selector})
                else:
                    # 便捷方法返回的格式
                    return self.ok({"success": True, "selector": params.selector, **raw_result})
            else:
                return self.ok({"success": True, "selector": params.selector})

        except Exception as e:
            return self.error_from_exception(e, recoverable=True)


# 便捷函数
async def click(
    selector: str,
    text: str = None,
    button: str = "left",
    count: int = 1,
    timeout: int = 5000,
    context: ExecutionContext = None
) -> Result[dict]:
    """
    点击元素

    Args:
        selector: CSS 选择器
        text: 元素文本（可选）
        button: 鼠标按钮
        count: 点击次数
        timeout: 超时时间
        context: 执行上下文

    Returns:
        点击结果
    """
    params = ClickParams(
        selector=selector,
        text=text,
        button=button,
        count=count,
        timeout=timeout,
    )
    tool = ClickTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["ClickTool", "ClickParams", "click"]
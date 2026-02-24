"""
截图工具

提供页面截图功能。
"""

from typing import Literal, Optional
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class ScreenshotParams(ToolParameters):
    """截图参数"""
    format: Literal["png", "jpeg"] = Field("png", description="图片格式")
    quality: int = Field(80, ge=1, le=100, description="图片质量（仅 JPEG 有效）")


@tool(name="browser.screenshot", description="截取当前页面截图")
class ScreenshotTool(Tool[ScreenshotParams, dict]):
    """截图工具"""

    async def execute(
        self,
        params: ScreenshotParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行截图"""
        from src.relay_client import NeuroneClient

        client = NeuroneClient()

        try:
            raw_result = await client.call_tool(
                "chrome_screenshot",
                format=params.format,
                quality=params.quality,
            )

            if isinstance(raw_result, dict):
                return self.ok({
                    "success": True,
                    "dataUrl": raw_result.get("dataUrl"),
                    "format": params.format,
                })
            else:
                return self.fail("截图返回格式错误")

        except Exception as e:
            return self.error_from_exception(e)


# 便捷函数
async def screenshot(
    format: str = "png",
    quality: int = 80,
    context: ExecutionContext = None
) -> Result[dict]:
    """截取页面截图"""
    params = ScreenshotParams(format=format, quality=quality)  # type: ignore
    tool = ScreenshotTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["ScreenshotTool", "ScreenshotParams", "screenshot"]
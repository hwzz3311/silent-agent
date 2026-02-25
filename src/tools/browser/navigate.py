"""
导航工具

提供页面导航功能。
"""

from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class NavigateParams(ToolParameters):
    """导航参数"""
    url: str = Field(..., description="目标 URL")
    new_tab: bool = Field(True, description="是否在新标签页打开")
    timeout: int = Field(30000, ge=0, le=120000, description="等待页面加载超时（毫秒）")


@tool(name="browser.navigate", description="导航到指定 URL")
class NavigateTool(Tool[NavigateParams, dict]):
    """导航工具"""

    async def execute(
        self,
        params: NavigateParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行导航"""
        import logging
        from src.relay_client import SilentAgentClient

        logger = logging.getLogger("navigate")

        # 优先使用已连接的 client（从 context 传入），避免重复创建连接
        client = getattr(context, 'client', None)
        if not client:
            logger.info("[NavigateTool] context 中无 client，创建新的 SilentAgentClient")
            client = SilentAgentClient()
            await client.connect()
        else:
            logger.info(f"[NavigateTool] 使用 context.client: {type(client)}")

        try:
            logger.info(f"[NavigateTool] 开始导航到: {params.url}, new_tab={params.new_tab}")
            logger.info(f"[NavigateTool] 调用 client.call_tool 之前的 client 状态: is_connected={client.is_connected if hasattr(client, 'is_connected') else 'N/A'}")
            # timeout 参数是毫秒，需要转换为秒
            timeout_seconds = params.timeout / 1000 if params.timeout else 30
            raw_result = await client.call_tool(
                "chrome_navigate",
                url=params.url,
                newTab=params.new_tab,
                timeout=timeout_seconds,
            )
            logger.info(f"[NavigateTool] 导航返回: {raw_result}")

            if isinstance(raw_result, dict):
                if raw_result.get("content"):
                    content = raw_result["content"]
                    is_error = raw_result.get("isError", False)
                    if is_error:
                        error_text = content[0].get("text", "导航失败") if content else "导航失败"
                        return self.fail(error_text)
                    else:
                        return self.ok({"success": True, "url": params.url})
                else:
                    return self.ok({
                        "success": True,
                        "url": params.url,
                        "tabId": raw_result.get("tabId"),
                        "title": raw_result.get("title"),
                        **raw_result
                    })
            else:
                return self.ok({"success": True, "url": params.url})

        except Exception as e:
            logger.error(f"[NavigateTool] 导航异常: {e}")
            return self.error_from_exception(e)


# 便捷函数
async def navigate(
    url: str,
    new_tab: bool = True,
    timeout: int = 30000,
    context: ExecutionContext = None
) -> Result[dict]:
    """导航到 URL"""
    params = NavigateParams(url=url, new_tab=new_tab, timeout=timeout)
    tool = NavigateTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["NavigateTool", "NavigateParams", "navigate"]
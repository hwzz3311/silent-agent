"""
无障碍树工具

提供获取无障碍树的功能：
- extension 模式：通过扩展 DOM 模拟（现有）
- puppeteer 模式：通过 Puppeteer 获取真实树
- hybrid 模式：通过 Puppeteer CDP 获取真实树
"""

from typing import Optional, Literal
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result
from src.browser import BrowserClientFactory, BrowserMode


class A11yTreeParams(ToolParameters):
    """无障碍树参数"""
    action: Literal["get_tree", "get_focused", "get_node", "query"] = Field(
        "get_tree", description="操作类型"
    )
    node_id: Optional[str] = Field(None, description="节点 ID (用于 get_node)")
    predicate: Optional[dict] = Field(None, description="查询谓词 (用于 query)")
    limit: int = Field(100, ge=1, le=1000, description="返回节点数量限制")
    # 新增：强制使用真实树获取
    use_real_tree: bool = Field(False, description="强制使用真实无障碍树（通过 Puppeteer）")


@tool(name="browser.a11y_tree", description="获取无障碍树（支持真实树）")
class A11yTreeTool(Tool[A11yTreeParams, dict]):
    """无障碍树工具

    根据上下文中的 browser_mode 选择不同的获取方式：
    - extension: 通过扩展 DOM 模拟（原有方式）
    - puppeteer: 通过 Puppeteer 获取真实树
    - hybrid: 通过 Puppeteer CDP 获取完整真实树
    """

    async def execute(
        self,
        params: A11yTreeParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行获取无障碍树"""
        browser_mode = context.browser_mode or "extension"

        # 如果指定了 use_real_tree 或使用 puppeteer/hybrid 模式，尝试获取真实树
        if params.use_real_tree or browser_mode in ("puppeteer", "hybrid"):
            return await self._get_real_tree(params, browser_mode)
        else:
            # 传统扩展模式
            return await self._get_simulated_tree(params, context)

    async def _get_real_tree(
        self,
        params: A11yTreeParams,
        browser_mode: str
    ) -> Result[dict]:
        """通过 Puppeteer 获取真实无障碍树"""
        try:
            # 通过工厂获取浏览器客户端
            client = await BrowserClientFactory.get_client()

            # 调用获取无障碍树
            raw_result = await client.get_a11y_tree(
                action=params.action,
                limit=params.limit,
                tab_id=params.node_id,
            )

            if isinstance(raw_result, dict):
                if raw_result.get("success"):
                    return self.ok(raw_result.get("data", raw_result))
                else:
                    error_msg = raw_result.get("error", "获取真实树失败")
                    # 如果获取真实树失败，回退到模拟树
                    if browser_mode == "hybrid":
                        return await self._get_simulated_tree_fallback(params)
                    return self.fail(error_msg)
            return self.ok(raw_result)

        except ImportError as e:
            # Puppeteer 未安装，回退到扩展模式
            return self.fail(f"Puppeteer 未安装: {e}", recoverable=True)
        except Exception as e:
            # 其他错误，尝试回退
            return self.error_from_exception(e, recoverable=True)

    async def _get_simulated_tree(
        self,
        params: A11yTreeParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """通过扩展获取模拟无障碍树（原有方式）"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            raw_result = await client.call_tool(
                "a11y_tree",
                action=params.action,
                nodeId=params.node_id,
                predicate=params.predicate,
                limit=params.limit,
            )

            if isinstance(raw_result, dict):
                if raw_result.get("content"):
                    content = raw_result["content"]
                    is_error = raw_result.get("isError", False)
                    if is_error:
                        error_text = content[0].get("text", "获取失败") if content else "获取失败"
                        return self.fail(error_text)
                    else:
                        data = content[0].get("text", "")
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

    async def _get_simulated_tree_fallback(
        self,
        params: A11yTreeParams
    ) -> Result[dict]:
        """回退到模拟树（hybrid 模式失败时）"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        try:
            raw_result = await client.call_tool(
                "a11y_tree",
                action=params.action,
                limit=params.limit,
            )

            if isinstance(raw_result, dict):
                if raw_result.get("content"):
                    content = raw_result["content"]
                    data = content[0].get("text", "")
                    try:
                        import json
                        result_data = json.loads(data)
                        # 标记为模拟树
                        result_data["_warning"] = "使用模拟树（真实树获取失败）"
                        return self.ok(result_data)
                    except (json.JSONDecodeError, IndexError):
                        return self.ok(content[0].get("text") if content else None)
                else:
                    return self.ok(raw_result)
            else:
                return self.ok(raw_result)

        except Exception as e:
            return self.error_from_exception(e)


# 便捷函数
async def get_a11y_tree(
    limit: int = 100,
    context: ExecutionContext = None,
    use_real_tree: bool = False
) -> Result[dict]:
    """获取完整无障碍树

    Args:
        limit: 返回节点数量限制
        context: 执行上下文
        use_real_tree: 是否使用真实树（通过 Puppeteer）
    """
    params = A11yTreeParams(action="get_tree", limit=limit, use_real_tree=use_real_tree)
    tool = A11yTreeTool()
    ctx = context or ExecutionContext()
    return await tool.execute_with_retry(params, ctx)


async def get_focused_element(
    context: ExecutionContext = None,
    use_real_tree: bool = False
) -> Result[dict]:
    """获取聚焦元素"""
    params = A11yTreeParams(action="get_focused", use_real_tree=use_real_tree)
    tool = A11yTreeTool()
    ctx = context or ExecutionContext()
    return await tool.execute_with_retry(params, ctx)


async def query_a11y_tree(
    predicate: dict,
    limit: int = 100,
    context: ExecutionContext = None,
    use_real_tree: bool = False
) -> Result[dict]:
    """查询无障碍树"""
    params = A11yTreeParams(action="query", predicate=predicate, limit=limit, use_real_tree=use_real_tree)
    tool = A11yTreeTool()
    ctx = context or ExecutionContext()
    return await tool.execute_with_retry(params, ctx)


__all__ = ["A11yTreeTool", "A11yTreeParams", "get_a11y_tree", "get_focused_element", "query_a11y_tree"]
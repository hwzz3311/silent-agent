"""
无障碍树工具

提供获取模拟无障碍树的功能。
"""

from typing import Optional, Literal
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class A11yTreeParams(ToolParameters):
    """无障碍树参数"""
    action: Literal["get_tree", "get_focused", "get_node", "query"] = Field(
        "get_tree", description="操作类型"
    )
    node_id: Optional[str] = Field(None, description="节点 ID (用于 get_node)")
    predicate: Optional[dict] = Field(None, description="查询谓词 (用于 query)")
    limit: int = Field(100, ge=1, le=1000, description="返回节点数量限制")


@tool(name="browser.a11y_tree", description="获取模拟无障碍树")
class A11yTreeTool(Tool[A11yTreeParams, dict]):
    """无障碍树工具"""

    async def execute(
        self,
        params: A11yTreeParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """执行获取无障碍树"""
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


# 便捷函数
async def get_a11y_tree(
    limit: int = 100,
    context: ExecutionContext = None
) -> Result[dict]:
    """获取完整无障碍树"""
    params = A11yTreeParams(action="get_tree", limit=limit)
    tool = A11yTreeTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


async def get_focused_element(context: ExecutionContext = None) -> Result[dict]:
    """获取聚焦元素"""
    params = A11yTreeParams(action="get_focused")
    tool = A11yTreeTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


async def query_a11y_tree(
    predicate: dict,
    limit: int = 100,
    context: ExecutionContext = None
) -> Result[dict]:
    """查询无障碍树"""
    params = A11yTreeParams(action="query", predicate=predicate, limit=limit)
    tool = A11yTreeTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["A11yTreeTool", "A11yTreeParams", "get_a11y_tree", "get_focused_element", "query_a11y_tree"]
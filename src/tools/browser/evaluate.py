"""
求值工具

提供在页面中执行函数调用的功能。
"""

from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class EvaluateParams(ToolParameters):
    """求值参数"""
    code: str = Field(..., description="要执行的 JavaScript 代码（函数体）")
    args: list = Field(default_factory=list, description="传递给函数的参数")
    world: str = Field("MAIN", description="执行世界")


@tool(name="browser.evaluate", description="在页面中执行 JavaScript 并获取返回值")
class EvaluateTool(Tool[EvaluateParams, any]):
    """求值工具"""

    async def execute(
        self,
        params: EvaluateParams,
        context: ExecutionContext
    ) -> Result[any]:
        """执行求值"""
        from src.relay_client import SilentAgentClient

        # 优先使用已连接的 client（从 context 传入），避免重复创建连接
        client = getattr(context, 'client', None)
        if not client:
            # 如果 context 中没有 client，则创建新的并连接
            client = SilentAgentClient()
            await client.connect()

        try:
            # 构建可执行代码
            args_str = ", ".join(f"arg{i}" for i in range(len(params.args)))
            full_code = f"""
            (function() {{
                const args = [{', '.join(f'JSON.parse(arg{i})' for i in range(len(params.args)))}];
                return ({params.code})({args_str});
            }})()
            """

            # 获取 tab_id 用于日志
            tab_id = context.tab_id if context else None

            # 详细日志 - 打印将要执行的 JS 代码
            print(f"[EvaluateTool.execute] tab_id={tab_id}, world={params.world}")
            print(f"[EvaluateTool.execute] 即将执行的 JS 代码:\n{full_code}")

            raw_result = await client.call_tool(
                "inject_script",
                code=full_code,
                world=params.world,
            )

            print(f"[EvaluateTool.execute] inject_script 返回结果: {raw_result}")

            return self.ok(raw_result)

        except Exception as e:
            print(f"[EvaluateTool.execute] 执行失败 - tab_id={context.tab_id if context else None}, error: {e}")
            return self.error_from_exception(e)


# 便捷函数
async def evaluate(
    code: str,
    args: list = None,
    world: str = "MAIN",
    context: ExecutionContext = None
) -> Result[any]:
    """执行 JavaScript 并获取返回值"""
    params = EvaluateParams(code=code, args=args or [], world=world)
    tool = EvaluateTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = ["EvaluateTool", "EvaluateParams", "evaluate"]
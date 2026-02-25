"""
脚本注入工具

在小红书页面中注入并执行 JavaScript，支持跨世界（ISOLATED → MAIN）通信。

迁移自: src/tools/xhs/xhs_inject_script.py
"""

import json
from typing import Literal, Optional, Any
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result


class InjectScriptParams(ToolParameters):
    """脚本注入参数"""
    code: str = Field(
        ...,
        description="要执行的 JavaScript 代码"
    )
    world: Literal["MAIN", "ISOLATED"] = Field(
        "ISOLATED",
        description="执行世界: MAIN=页面上下文, ISOLATED=隔离世界"
    )
    args: Optional[dict] = Field(
        None,
        description="传递给代码的参数（会自动注入为 args 变量）"
    )
    tab_id: Optional[int] = Field(
        None,
        description="标签页 ID，默认使用当前活动标签页"
    )
    timeout: Optional[int] = Field(
        30000,
        description="执行超时时间（毫秒）"
    )


@tool(
    name="xhs_inject_script",
    description="在小红书页面中注入并执行 JavaScript，支持跨世界通信",
    category="browser",
    version="1.0.0",
    tags=["xhs", "xiaohongshu", "inject", "script", "javascript"]
)
class InjectScriptTool(Tool[InjectScriptParams, Any]):
    """脚本注入工具"""

    async def execute(
        self,
        params: InjectScriptParams,
        context: ExecutionContext
    ) -> Result[Any]:
        """执行注入脚本"""
        try:
            # 根据执行世界选择不同的执行策略
            if params.world == "MAIN":
                # MAIN 世界：直接执行
                return await self._execute_in_main_world(params, context)
            else:
                # ISOLATED 世界：可能需要跨世界通信
                return await self._execute_in_isolated_world(params, context)

        except Exception as e:
            return self.error_from_exception(e)

    async def _execute_in_main_world(
        self,
        params: InjectScriptParams,
        context: ExecutionContext
    ) -> Result[Any]:
        """在 MAIN 世界执行代码"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        # 包装代码以接收参数
        wrapped_code = self._wrap_code_with_args(params.code, params.args)

        try:
            raw_result = await client.call_tool(
                "inject_script",
                code=wrapped_code,
                world="MAIN",
            )

            return self._parse_result(raw_result)

        except Exception as e:
            return self.error_from_exception(e)

    async def _execute_in_isolated_world(
        self,
        params: InjectScriptParams,
        context: ExecutionContext
    ) -> Result[Any]:
        """在 ISOLATED 世界执行代码"""
        from src.relay_client import SilentAgentClient

        client = SilentAgentClient()

        # 包装代码以接收参数
        wrapped_code = self._wrap_code_with_args(params.code, params.args)

        try:
            raw_result = await client.call_tool(
                "inject_script",
                code=wrapped_code,
                world="ISOLATED",
            )

            return self._parse_result(raw_result)

        except Exception as e:
            return self.error_from_exception(e)

    def _wrap_code_with_args(self, code: str, args: Optional[dict]) -> str:
        """包装代码以接收参数"""
        if not args:
            return code

        # 将参数转换为 JSON 字符串
        args_json = json.dumps(args)

        # 包装代码
        return f"""
        (function() {{
            const args = {args_json};
            {code}
        }})()
        """

    def _parse_result(self, raw_result: Any) -> Result[Any]:
        """解析工具返回结果"""
        if isinstance(raw_result, dict):
            if raw_result.get("content"):
                content = raw_result["content"]
                is_error = raw_result.get("isError", False)

                if is_error:
                    error_text = content[0].get("text", "脚本执行失败")
                    return self.fail(error_text)
                else:
                    # 解析内容
                    try:
                        data = content[0].get("text", "")
                        if data:
                            parsed = json.loads(data)
                            return self.ok(parsed)
                    except (json.JSONDecodeError, IndexError):
                        return self.ok(content[0].get("text") if content else None)
            else:
                return self.ok(raw_result)
        else:
            return self.ok(raw_result)


# ========== 便捷函数 ==========

async def inject_script(
    code: str,
    world: str = "ISOLATED",
    args: Optional[dict] = None,
    tab_id: Optional[int] = None,
    timeout: Optional[int] = None,
    context: ExecutionContext = None
) -> Result[Any]:
    """在小红书页面中注入脚本"""
    params = InjectScriptParams(
        code=code,
        world=world,
        args=args,
        tab_id=tab_id,
        timeout=timeout
    )
    tool = InjectScriptTool()
    return await tool.execute_with_retry(params, context or ExecutionContext())


__all__ = [
    "InjectScriptTool",
    "InjectScriptParams",
    "inject_script",
]
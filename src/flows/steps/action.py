"""
动作步骤实现

执行工具调用的步骤。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from .base import FlowStep, StepType, StepStatus, StepConfig, StepResult
from .. import FlowContext


class ActionStep(FlowStep):
    """
    动作步骤

    执行工具调用的基本步骤。

    Attributes:
        tool: 工具名称
        params: 工具参数
    """

    def __init__(
        self,
        step_id: str,
        name: str,
        tool: str,
        params: Dict[str, Any] = None,
        config: StepConfig = None,
        next_on_success: str = None,
        next_on_failure: str = None,
    ):
        super().__init__(
            step_id=step_id,
            name=name,
            config=config,
            next_on_success=next_on_success,
            next_on_failure=next_on_failure,
        )
        self.tool = tool
        self.params = params or {}

    @classmethod
    def get_step_type(cls) -> StepType:
        return StepType.ACTION

    async def execute(
        self,
        context: FlowContext,
        tool_caller: callable = None
    ):
        """
        执行工具调用

        Args:
            context: 流程上下文
            tool_caller: 工具调用函数

        Returns:
            StepResult: 步骤执行结果
        """
        start_time = datetime.utcnow()
        status = StepStatus.RUNNING
        output = None
        error = None

        try:
            # 解析参数（替换变量占位符）
            resolved_params = self._resolve_params(context)

            # 执行工具调用
            if tool_caller:
                result = await tool_caller(self.tool, resolved_params)
                if result.success:
                    output = result.data
                    status = StepStatus.COMPLETED
                else:
                    error = result.error.get("message") if isinstance(result.error, dict) else str(result.error)
                    status = StepStatus.FAILED
            else:
                # 无工具调用器时跳过
                status = StepStatus.SKIPPED
                output = {"skipped": "no tool caller"}

        except Exception as e:
            status = StepStatus.FAILED
            error = str(e)

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # 确定下一步
        next_step = None
        if status == StepStatus.COMPLETED:
            next_step = self.next_on_success
        elif status == StepStatus.FAILED:
            next_step = self.next_on_failure if self.config.continue_on_error else None

        return StepResult(
            step_id=self.id,
            step_name=self.name,
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            output=self._serialize_output(output),
            error=error,
            next_step=next_step,
        )

    def _resolve_params(self, context: FlowContext) -> Dict[str, Any]:
        """解析参数中的变量占位符"""
        resolved = {}
        for key, value in self.params.items():
            resolved[key] = self._resolve_value(context, value)
        return resolved

    def _resolve_value(self, context: FlowContext, value: Any) -> Any:
        """解析单个值中的变量占位符"""
        if isinstance(value, str):
            # 检查是否为变量占位符
            if value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                return context.get_variable(var_name, value)
        elif isinstance(value, dict):
            return {k: self._resolve_value(context, v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_value(context, item) for item in value]
        return value

    def __repr__(self) -> str:
        return (
            f"ActionStep(id={self.id}, name={self.name}, "
            f"tool={self.tool})"
        )
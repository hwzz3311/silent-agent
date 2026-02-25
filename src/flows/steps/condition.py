"""
条件步骤实现

支持条件分支的步骤。
"""

from datetime import datetime
from typing import Any, Dict, List

from .base import FlowStep, StepType, StepStatus, StepConfig
from .. import FlowContext


class ConditionStep(FlowStep):
    """
    条件步骤

    根据条件评估结果选择执行分支。

    Attributes:
        condition: 条件表达式
        on_true: 条件为真时执行的步骤列表
        on_false: 条件为假时执行的步骤列表
    """

    def __init__(
        self,
        step_id: str,
        name: str,
        condition: str,
        on_true: List[Dict[str, Any]] = None,
        on_false: List[Dict[str, Any]] = None,
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
        self.condition = condition
        self.on_true = on_true or []
        self.on_false = on_false or []

    @classmethod
    def get_step_type(cls) -> StepType:
        return StepType.CONDITION

    async def execute(
        self,
        context: FlowContext,
        tool_caller: callable = None,
        step_factory: callable = None
    ):
        """
        执行条件判断

        Args:
            context: 流程上下文
            tool_caller: 工具调用函数
            step_factory: 步骤工厂函数（用于创建子步骤）

        Returns:
            StepResult: 步骤执行结果
        """
        start_time = datetime.utcnow()
        status = StepStatus.RUNNING
        output = None
        error = None
        branch_executed = None

        try:
            # 评估条件
            condition_result = self._evaluate_condition(context, self.condition)

            # 执行相应分支
            if condition_result:
                branch_executed = "true"
                if self.on_true and step_factory:
                    for step_data in self.on_true:
                        step = step_factory(step_data)
                        result = await step.execute(context, tool_caller, step_factory)
                        if result.status == StepStatus.FAILED:
                            status = StepStatus.FAILED
                            error = result.error
                            break
                        if result.status == StepStatus.COMPLETED:
                            output = result.output
                output = {"condition": condition_result, "branch": "true"}
            else:
                branch_executed = "false"
                if self.on_false and step_factory:
                    for step_data in self.on_false:
                        step = step_factory(step_data)
                        result = await step.execute(context, tool_caller, step_factory)
                        if result.status == StepStatus.FAILED:
                            status = StepStatus.FAILED
                            error = result.error
                            break
                output = {"condition": condition_result, "branch": "false"}

            if status == StepStatus.RUNNING:
                status = StepStatus.COMPLETED

        except Exception as e:
            status = StepStatus.FAILED
            error = str(e)

        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return StepResult(
            step_id=self.id,
            step_name=self.name,
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            output=self._serialize_output(output),
            error=error,
            next_step=self.next_on_success,
        )

    def __repr__(self) -> str:
        return (
            f"ConditionStep(id={self.id}, name={self.name}, "
            f"condition={self.condition})"
        )
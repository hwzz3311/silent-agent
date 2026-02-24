"""
循环步骤实现

支持循环执行的步骤。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import FlowStep, StepType, StepStatus, StepConfig, StepResult
from .. import FlowContext


class LoopStep(FlowStep):
    """
    循环步骤

    支持 while/for 循环。

    Attributes:
        loop_type: 循环类型 (while, for, foreach)
        condition: 循环条件（while 类型）
        items: 迭代列表（foreach 类型）
        loop_var: 循环变量名
        max_iterations: 最大迭代次数
        body: 循环体步骤列表
    """

    def __init__(
        self,
        step_id: str,
        name: str,
        loop_type: str = "while",
        condition: str = None,
        items: List[Any] = None,
        loop_var: str = "item",
        max_iterations: int = 1000,
        body: List[Dict[str, Any]] = None,
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
        self.loop_type = loop_type
        self.condition = condition
        self.items = items or []
        self.loop_var = loop_var
        self.max_iterations = max_iterations
        self.body = body or []

    @classmethod
    def get_step_type(cls) -> StepType:
        return StepType.LOOP

    async def execute(
        self,
        context: FlowContext,
        tool_caller: callable = None,
        step_factory: callable = None
    ):
        """
        执行循环

        Args:
            context: 流程上下文
            tool_caller: 工具调用函数
            step_factory: 步骤工厂函数

        Returns:
            StepResult: 步骤执行结果
        """
        start_time = datetime.utcnow()
        status = StepStatus.RUNNING
        output = None
        error = None

        try:
            iteration = 0
            iterations_data = []

            if self.loop_type == "while":
                # While 循环
                while self._evaluate_condition(context, self.condition):
                    if iteration >= self.max_iterations:
                        error = f"达到最大迭代次数: {self.max_iterations}"
                        break

                    # 执行循环体
                    for step_data in self.body:
                        step = step_factory(step_data)
                        result = await step.execute(context, tool_caller, step_factory)
                        if result.status == StepStatus.FAILED:
                            status = StepStatus.FAILED
                            error = result.error
                            break
                        iterations_data.append({
                            "iteration": iteration,
                            "step": result.step_id,
                            "status": result.status.value,
                        })
                        if result.next_step:
                            # 如果有中断信号
                            break

                    if status == StepStatus.FAILED:
                        break

                    iteration += 1

            elif self.loop_type == "foreach":
                # ForEach 循环
                for item in self.items:
                    if iteration >= self.max_iterations:
                        error = f"达到最大迭代次数: {self.max_iterations}"
                        break

                    # 设置循环变量
                    context.set_variable(self.loop_var, item)

                    # 执行循环体
                    for step_data in self.body:
                        step = step_factory(step_data)
                        result = await step.execute(context, tool_caller, step_factory)
                        if result.status == StepStatus.FAILED:
                            status = StepStatus.FAILED
                            error = result.error
                            break
                        iterations_data.append({
                            "iteration": iteration,
                            "item": str(item)[:100],
                            "status": result.status.value,
                        })

                    if status == StepStatus.FAILED:
                        break

                    iteration += 1

            else:
                # For 循环（简化为指定次数的循环）
                count = int(self.condition) if self.condition else 0
                for i in range(count):
                    if iteration >= self.max_iterations:
                        break

                    context.set_variable("i", iteration)

                    for step_data in self.body:
                        step = step_factory(step_data)
                        result = await step.execute(context, tool_caller, step_factory)
                        if result.status == StepStatus.FAILED:
                            status = StepStatus.FAILED
                            error = result.error
                            break

                    if status == StepStatus.FAILED:
                        break

                    iteration += 1

            output = {
                "iterations": iteration,
                "iterations_data": iterations_data[:100],  # 限制保存的数据量
            }

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
            f"LoopStep(id={self.id}, name={self.name}, "
            f"type={self.loop_type})"
        )
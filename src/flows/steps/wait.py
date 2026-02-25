"""
等待步骤实现

支持等待条件的步骤。
"""

import asyncio
from datetime import datetime

from .base import FlowStep, StepType, StepStatus, StepConfig, StepResult
from .. import FlowContext


class WaitStep(FlowStep):
    """
    等待步骤

    支持等待指定条件或时间。

    Attributes:
        wait_type: 等待类型 (time, condition, element)
        duration: 等待时间（毫秒）
        condition: 等待条件表达式
        interval: 检查间隔（毫秒）
    """

    def __init__(
        self,
        step_id: str,
        name: str,
        wait_type: str = "time",
        duration: int = 1000,
        condition: str = None,
        interval: int = 500,
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
        self.wait_type = wait_type
        self.duration = duration
        self.condition = condition
        self.interval = interval

    @classmethod
    def get_step_type(cls) -> StepType:
        return StepType.WAIT

    async def execute(
        self,
        context: FlowContext,
        tool_caller: callable = None
    ):
        """
        执行等待

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
            if self.wait_type == "time":
                # 等待指定时间
                await asyncio.sleep(self.duration / 1000)
                output = {"waited_ms": self.duration}

            elif self.wait_type == "condition":
                # 等待条件满足
                waited_ms = 0
                timeout_ms = self.config.timeout or self.duration

                while not self._evaluate_condition(context, self.condition):
                    if waited_ms >= timeout_ms:
                        error = "等待条件超时"
                        status = StepStatus.FAILED
                        break

                    await asyncio.sleep(self.interval / 1000)
                    waited_ms += self.interval

                if status == StepStatus.RUNNING:
                    output = {"waited_ms": waited_ms, "condition_met": True}

            elif self.wait_type == "element":
                # 等待元素出现（通过工具调用）
                if tool_caller:
                    result = await tool_caller("browser.wait", {
                        "selector": self.condition,  # 使用 condition 作为选择器
                        "timeout": self.config.timeout or self.duration,
                    })

                    if result.success:
                        output = {"waited": True, "selector": self.condition}
                    else:
                        error = "等待元素超时"
                        status = StepStatus.FAILED
                else:
                    # 无工具调用器时的降级处理
                    await asyncio.sleep(self.duration / 1000)
                    output = {"waited_ms": self.duration, "fallback": True}

            else:
                # 未知类型，降级为等待
                await asyncio.sleep(self.duration / 1000)
                output = {"waited_ms": self.duration, "type": self.wait_type}

            if status == StepStatus.RUNNING:
                status = StepStatus.COMPLETED

        except asyncio.CancelledError:
            status = StepStatus.CANCELLED
            error = "等待被取消"

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
            f"WaitStep(id={self.id}, name={self.name}, "
            f"type={self.wait_type})"
        )
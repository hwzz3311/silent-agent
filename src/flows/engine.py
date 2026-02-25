"""
流程引擎核心模块

提供流程执行的核心引擎类。
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from . import StepResult
from .context import FlowContext
from .steps import FlowStep, StepFactory, StepStatus
from .parsers import FlowParser


class FlowEngine:
    """
    流程引擎

    负责流程定义解析、步骤调度和执行控制。

    Attributes:
        parser: 流程解析器
        step_factory: 步骤工厂
    """

    def __init__(self, parser: FlowParser = None):
        self.parser = parser or FlowParser()
        self.step_factory = StepFactory()
        self._running_flows: Dict[str, FlowContext] = {}

    @property
    def running_flows(self) -> Dict[str, FlowContext]:
        """获取运行中的流程"""
        return {k: v for k, v in self._running_flows.items() if v.is_running}

    async def load_flow(
        self,
        flow_data: Dict[str, Any],
        flow_id: str = None
    ) -> FlowContext:
        """
        加载并解析流程定义

        Args:
            flow_data: 流程定义数据
            flow_id: 流程 ID

        Returns:
            FlowContext: 流程上下文
        """
        flow_id = flow_id or str(uuid.uuid4())
        flow_name = flow_data.get("name", "Unnamed Flow")
        variables = flow_data.get("variables", [])
        steps_data = flow_data.get("steps", [])

        # 创建上下文
        context = FlowContext(
            flow_id=flow_id,
            flow_name=flow_name,
            initial_variables=self._parse_variables(variables),
            timeout=flow_data.get("timeout"),
        )

        # 解析并验证步骤
        steps = self._parse_steps(steps_data)
        context._steps = steps
        context._step_index_map = {step.id: i for i, step in enumerate(steps)}

        return context

    async def execute(
        self,
        flow_data: Dict[str, Any],
        variables: Dict[str, Any] = None,
        tool_caller: Callable[[str, Dict], Any] = None,
        timeout: int = None,
    ) -> FlowContext:
        """
        执行流程

        Args:
            flow_data: 流程定义数据
            variables: 初始变量
            tool_caller: 工具调用函数
            timeout: 超时时间（毫秒）

        Returns:
            FlowContext: 流程执行上下文
        """
        # 加载流程
        context = await self.load_flow(flow_data)
        if variables:
            context.merge_variables(variables)

        # 设置超时
        if timeout:
            context.timeout = timeout

        # 开始执行
        context.start()
        self._running_flows[context.flow_id] = context

        try:
            # 执行所有步骤
            await self._execute_all_steps(context, tool_caller)

            # 完成流程
            context.complete()

        except asyncio.CancelledError:
            context.cancel()
            raise
        except Exception as e:
            context.fail(e)
            raise
        finally:
            self._running_flows.pop(context.flow_id, None)

        return context

    async def execute_step(
        self,
        context: FlowContext,
        step_id: str,
        tool_caller: Callable[[str, Dict], Any] = None
    ) -> FlowContext:
        """
        执行单个步骤

        Args:
            context: 流程上下文
            step_id: 步骤 ID
            tool_caller: 工具调用函数

        Returns:
            FlowContext: 更新后的上下文
        """
        step_index = context._step_index_map.get(step_id)
        if step_index is None or step_index >= len(context._steps):
            raise ValueError(f"无效的步骤 ID: {step_id}")

        context.current_step = context._steps[step_index]
        context.current_step_index = step_index

        # 执行步骤
        result = await context.current_step.execute(
            context,
            tool_caller,
            lambda data: self.step_factory.create(data)
        )

        # 更新上下文
        context._record_step_result(result)

        # 处理下一步
        if result.next_step:
            await self.execute_step(context, result.next_step, tool_caller)

        return context

    async def _execute_all_steps(
        self,
        context: FlowContext,
        tool_caller: Callable[[str, Dict], Any]
    ) -> None:
        """执行所有步骤（顺序执行）"""
        for step in context._steps:
            if context.is_cancelled:
                break

            context.current_step = step

            # 验证前置条件
            if not await step.validate(context):
                context._record_step_result(StepResult(
                    step_id=step.id,
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    start_time=datetime.utcnow(),
                    output={"skipped": "condition_not_met"},
                ))
                continue

            # 执行步骤
            result = await step.execute(
                context,
                tool_caller,
                lambda data: self.step_factory.create(data)
            )

            # 记录结果
            context._record_step_result(result)

            # 处理错误
            if result.status == StepStatus.FAILED:
                if not step.config.continue_on_error:
                    raise Exception(f"步骤执行失败: {step.name} - {result.error}")

            # 处理分支跳转
            if result.next_step:
                await self._execute_from_step(context, result.next_step, tool_caller)

    async def _execute_from_step(
        self,
        context: FlowContext,
        start_step_id: str,
        tool_caller: Callable[[str, Dict], Any]
    ) -> None:
        """从指定步骤开始执行"""
        step_index = context._step_index_map.get(start_step_id)
        if step_index is None:
            raise ValueError(f"无效的步骤 ID: {start_step_id}")

        # 找到当前步骤的索引
        current_index = context.current_step_index if context.current_step else -1

        # 从指定步骤开始执行到流程结束
        for i in range(max(step_index, current_index + 1), len(context._steps)):
            if context.is_cancelled:
                break

            step = context._steps[i]

            if not await step.validate(context):
                context._record_step_result(StepResult(
                    step_id=step.id,
                    step_name=step.name,
                    status=StepStatus.SKIPPED,
                    start_time=datetime.utcnow(),
                    output={"skipped": "condition_not_met"},
                ))
                continue

            result = await step.execute(
                context,
                tool_caller,
                lambda data: self.step_factory.create(data)
            )

            context._record_step_result(result)

            if result.status == StepStatus.FAILED:
                if not step.config.continue_on_error:
                    raise Exception(f"步骤执行失败: {step.name} - {result.error}")

            if result.next_step:
                await self._execute_from_step(context, result.next_step, tool_caller)
                break

    def _record_step_result(self, context: FlowContext, result) -> None:
        """记录步骤结果"""
        context.step_results.append(result.to_dict())

    def _parse_variables(self, variables: List[Dict[str, Any]]) -> Dict[str, Any]:
        """解析变量定义"""
        result = {}
        for var in variables:
            name = var.get("name")
            default = var.get("default")
            if name is not None:
                result[name] = default
        return result

    def _parse_steps(self, steps_data: List[Dict[str, Any]]) -> List[FlowStep]:
        """解析步骤定义"""
        steps = []
        for step_data in steps_data:
            step = self.step_factory.create(step_data)
            steps.append(step)
        return steps

    def cancel(self, execution_id: str) -> bool:
        """
        取消执行

        Args:
            execution_id: 执行 ID

        Returns:
            bool: 是否取消成功
        """
        context = self._running_flows.get(execution_id)
        if context:
            context.cancel()
            return True
        return False

    def get_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行状态

        Args:
            execution_id: 执行 ID

        Returns:
            状态信息字典
        """
        context = self._running_flows.get(execution_id)
        if context:
            return context.snapshot()
        return None

    def list_running(self) -> List[Dict[str, Any]]:
        """列出运行中的执行"""
        return [ctx.snapshot() for ctx in self._running_flows.values() if ctx.is_running]


# ========== 便捷函数 ==========

async def run_flow(
    flow_data: Dict[str, Any],
    variables: Dict[str, Any] = None,
    tool_caller: Callable[[str, Dict], Any] = None,
    timeout: int = None,
) -> FlowContext:
    """
    执行流程（便捷函数）

    Args:
        flow_data: 流程定义数据
        variables: 初始变量
        tool_caller: 工具调用函数
        timeout: 超时时间

    Returns:
        FlowContext: 执行结果
    """
    engine = FlowEngine()
    return await engine.execute(flow_data, variables, tool_caller, timeout)


__all__ = [
    "FlowEngine",
    "run_flow",
]
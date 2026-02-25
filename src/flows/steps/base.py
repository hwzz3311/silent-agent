"""
流程步骤基类模块

定义所有流程步骤的抽象基类和公共接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Type
from enum import Enum
from pydantic import BaseModel

from src.flows.context import FlowContext


class StepType(str, Enum):
    """步骤类型"""
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    PARALLEL_BRANCH = "parallel_branch"
    WAIT = "wait"
    SUB_FLOW = "sub_flow"
    SET_VAR = "set_var"
    LOG = "log"


class StepStatus(str, Enum):
    """步骤执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class StepConfig(BaseModel):
    """步骤配置"""
    timeout: Optional[int] = None
    retry_count: int = 1
    retry_delay: int = 1000
    continue_on_error: bool = False
    condition: Optional[str] = None  # 条件表达式


@dataclass
class StepResult:
    """步骤执行结果"""
    step_id: str
    step_name: str
    status: StepStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    output: Optional[Any] = None
    error: Optional[str] = None
    next_step: Optional[str] = None  # 下一步骤 ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "output": self.output,
            "error": self.error,
            "next_step": self.next_step,
        }


class FlowStep(ABC):
    """
    流程步骤抽象基类

    所有流程步骤都必须继承此类并实现 execute 方法。

    Attributes:
        id: 步骤 ID
        name: 步骤名称
        type: 步骤类型
        config: 步骤配置
        next_on_success: 成功时下一步 ID
        next_on_failure: 失败时下一步 ID
    """

    def __init__(
        self,
        step_id: str,
        name: str,
        config: StepConfig = None,
        next_on_success: str = None,
        next_on_failure: str = None,
    ):
        self.id = step_id
        self.name = name
        self.type = self.get_step_type()
        self.config = config or StepConfig()
        self.next_on_success = next_on_success
        self.next_on_failure = next_on_failure

    @classmethod
    @abstractmethod
    def get_step_type(cls) -> StepType:
        """获取步骤类型"""
        ...

    @abstractmethod
    async def execute(
        self,
        context: FlowContext,
        tool_caller: callable = None
    ) -> StepResult:
        """
        执行步骤

        Args:
            context: 流程上下文
            tool_caller: 工具调用函数 (tool_name, params) -> Result

        Returns:
            StepResult: 步骤执行结果
        """
        ...

    async def validate(self, context: FlowContext) -> bool:
        """
        验证步骤是否可以执行

        Args:
            context: 流程上下文

        Returns:
            bool: 是否可以执行
        """
        # 检查条件
        if self.config.condition:
            result = self._evaluate_condition(context, self.config.condition)
            return result
        return True

    def _evaluate_condition(self, context: FlowContext, condition: str) -> bool:
        """
        评估条件表达式

        Args:
            context: 流程上下文
            condition: 条件表达式（如 "${count > 0}"）

        Returns:
            bool: 条件结果
        """
        try:
            # 替换变量
            expr = condition
            for key, value in context.variables.items():
                placeholder = f"${{{key}}}"
                if placeholder in expr:
                    if isinstance(value, str):
                        expr = expr.replace(placeholder, f'"{value}"')
                    else:
                        expr = expr.replace(placeholder, str(value))

            # 安全评估（仅允许简单表达式）
            # 警告：此方法存在安全风险，生产环境应使用安全的表达式解析器
            result = eval(expr, {"__builtins__": {}}, {})
            return bool(result)
        except Exception as e:
            print(f"[FlowStep] 条件评估失败: {condition}, error: {e}")
            return False

    def _serialize_output(self, output: Any) -> Any:
        """序列化输出（确保 JSON 可序列化）"""
        if output is None:
            return None
        if isinstance(output, (str, int, float, bool)):
            return output
        if isinstance(output, list):
            return [self._serialize_output(item) for item in output]
        if isinstance(output, dict):
            return {k: self._serialize_output(v) for k, v in output.items()}
        return str(output)

    def __repr__(self) -> str:
        return (
            f"FlowStep(id={self.id}, name={self.name}, "
            f"type={self.type.value})"
        )


# ========== 步骤工厂 ==========

class StepFactory:
    """步骤工厂"""

    _step_classes: Dict[StepType, Type[FlowStep]] = {}

    @classmethod
    def register(cls, step_type: StepType, step_class: Type[FlowStep]) -> None:
        """注册步骤类"""
        cls._step_classes[step_type] = step_class

    @classmethod
    def create(cls, step_data: Dict[str, Any]) -> FlowStep:
        """从数据创建步骤实例"""
        step_type = StepType(step_data.get("type", "action"))

        if step_type not in cls._step_classes:
            raise ValueError(f"Unknown step type: {step_type}")

        step_class = cls._step_classes[step_type]
        return step_class(**step_data)

    @classmethod
    def get_class(cls, step_type: StepType) -> Type[FlowStep]:
        """获取步骤类"""
        return cls._step_classes.get(step_type)


# ========== 步骤基类注册 ==========

# 导入具体步骤实现
from .action import ActionStep
from .condition import ConditionStep
from .loop import LoopStep
from .wait import WaitStep

# 注册基本步骤
StepFactory.register(StepType.ACTION, ActionStep)
StepFactory.register(StepType.CONDITION, ConditionStep)
StepFactory.register(StepType.LOOP, LoopStep)
StepFactory.register(StepType.WAIT, WaitStep)


__all__ = [
    "StepType",
    "StepStatus",
    "StepConfig",
    "StepResult",
    "FlowStep",
    "StepFactory",
]
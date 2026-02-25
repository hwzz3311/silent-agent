"""
流程执行上下文

管理流程执行过程中的上下文信息。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class FlowExecutionState(Enum):
    """流程执行状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FlowContext:
    """
    流程执行上下文

    管理流程执行过程中的所有状态信息。

    Attributes:
        flow_id: 流程 ID
        flow_name: 流程名称
        variables: 流程变量
        state: 执行状态
        current_step: 当前步骤索引
        step_results: 步骤结果列表
        start_time: 开始时间
        end_time: 结束时间
    """

    def __init__(
        self,
        flow_id: str = None,
        flow_name: str = None,
        initial_variables: Dict[str, Any] = None,
        timeout: int = None,
    ):
        self.flow_id = flow_id
        self.flow_name = flow_name
        self.variables = initial_variables or {}
        self.state = FlowExecutionState.IDLE
        self.current_step_index = 0
        self.current_step = None
        self.step_results: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.timeout = timeout
        self.error: Optional[Dict[str, Any]] = None
        self._call_stack: List[Dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.state == FlowExecutionState.RUNNING

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.state == FlowExecutionState.COMPLETED

    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.state == FlowExecutionState.FAILED

    @property
    def is_cancelled(self) -> bool:
        """是否已取消"""
        return self.state == FlowExecutionState.CANCELLED

    @property
    def duration_ms(self) -> int:
        """执行持续时间（毫秒）"""
        if self.start_time is None:
            return 0
        end = self.end_time or datetime.utcnow()
        return int((end - self.start_time).total_seconds() * 1000)

    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)

    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables[name] = value

    def has_variable(self, name: str) -> bool:
        """检查变量是否存在"""
        return name in self.variables

    def merge_variables(self, updates: Dict[str, Any]) -> None:
        """合并变量"""
        self.variables.update(updates)

    def start(self) -> None:
        """开始执行"""
        self.state = FlowExecutionState.RUNNING
        self.start_time = datetime.utcnow()

    def complete(self, result: Any = None) -> None:
        """完成执行"""
        self.state = FlowExecutionState.COMPLETED
        self.end_time = datetime.utcnow()
        self._record_result("completed", result)

    def fail(self, error: Exception) -> None:
        """执行失败"""
        self.state = FlowExecutionState.FAILED
        self.end_time = datetime.utcnow()
        self.error = {
            "type": type(error).__name__,
            "message": str(error),
        }
        self._record_result("failed", None, error)

    def cancel(self) -> None:
        """取消执行"""
        self.state = FlowExecutionState.CANCELLED
        self.end_time = datetime.utcnow()
        self._record_result("cancelled", None)

    def _record_result(self, status: str, result: Any = None, error: Exception = None) -> None:
        """记录执行结果"""
        self.step_results.append({
            "status": status,
            "result": result,
            "error": str(error) if error else None,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def push_scope(self, variables: Dict[str, Any] = None) -> None:
        """推入新的变量作用域"""
        self._call_stack.append({
            "variables": self.variables.copy(),
            "step_index": self.current_step_index,
        })
        if variables:
            self.variables.update(variables)

    def pop_scope(self) -> Dict[str, Any]:
        """弹出变量作用域"""
        if self._call_stack:
            snapshot = self._call_stack.pop()
            self.variables = snapshot["variables"]
            return snapshot
        return {}

    def snapshot(self) -> Dict[str, Any]:
        """获取上下文快照"""
        return {
            "flow_id": self.flow_id,
            "flow_name": self.flow_name,
            "state": self.state.value,
            "variables": self.variables.copy(),
            "current_step": self.current_step,
            "step_results_count": len(self.step_results),
            "duration_ms": self.duration_ms,
            "error": self.error,
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "flow_id": self.flow_id,
            "flow_name": self.flow_name,
            "variables": self.variables,
            "state": self.state.value,
            "current_step_index": self.current_step_index,
            "step_results": self.step_results,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "timeout": self.timeout,
            "error": self.error,
        }

    def __repr__(self) -> str:
        return (
            f"FlowContext(flow_id={self.flow_id}, "
            f"state={self.state.value}, "
            f"steps={len(self.step_results)})"
        )
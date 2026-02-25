"""
执行上下文模块

提供 ExecutionContext 和相关上下文管理功能。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class ExecutionState(Enum):
    """执行状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class VariableScope:
    """变量作用域"""
    variables: Dict[str, Any] = field(default_factory=dict)
    parent: Optional['VariableScope'] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def get(self, name: str, default: Any = None) -> Any:
        """获取变量（支持作用域链查找）"""
        scope = self
        while scope:
            if name in scope.variables:
                return scope.variables[name]
            scope = scope.parent
        return default

    def set(self, name: str, value: Any) -> None:
        """设置变量（当前作用域）"""
        self.variables[name] = value

    def define(self, name: str, value: Any) -> None:
        """定义变量（仅当不存在时）"""
        if not self.exists(name):
            self.variables[name] = value

    def exists(self, name: str) -> bool:
        """检查变量是否存在"""
        return self.get(name) is not None

    def remove(self, name: str) -> bool:
        """删除变量"""
        if name in self.variables:
            del self.variables[name]
            return True
        return False

    def snapshot(self) -> Dict[str, Any]:
        """获取当前作用域快照"""
        return {**self.variables}

    def merge(self, other: Dict[str, Any]) -> None:
        """合并变量"""
        self.variables.update(other)

    def __enter__(self) -> 'VariableScope':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


@dataclass
class ExecutionContext:
    """
    执行上下文

    Attributes:
        tab_id: 标签页 ID
        world: 执行世界 (MAIN/ISOLATED)
        timeout: 执行超时时间（毫秒）
        retry_count: 重试次数
        retry_delay: 重试间隔（毫秒）
        variables: 变量作用域
        state: 执行状态
        metadata: 额外元数据
    """
    tab_id: Optional[int] = None
    world: str = "MAIN"
    timeout: int = 30000
    retry_count: int = 1
    retry_delay: int = 1000
    variables: VariableScope = field(default_factory=VariableScope)
    state: ExecutionState = ExecutionState.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ========== 变量管理 ==========

    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)

    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables.set(name, value)

    def get_or_raise(self, name: str, message: str = None) -> Any:
        """获取变量，不存在则抛出异常"""
        value = self.variables.get(name)
        if value is None:
            raise ValueError(message or f"变量 '{name}' 未定义")
        return value

    def define_variable(self, name: str, value: Any) -> None:
        """定义变量（仅当不存在时）"""
        self.variables.define(name, value)

    def remove_variable(self, name: str) -> bool:
        """删除变量"""
        return self.variables.remove(name)

    def push_scope(self, variables: Dict[str, Any] = None) -> 'VariableScope':
        """推入新的变量作用域"""
        new_scope = VariableScope(parent=self.variables)
        if variables:
            new_scope.variables = {**variables}
        self.variables = new_scope
        return new_scope

    def pop_scope(self) -> Dict[str, Any]:
        """弹出变量作用域并返回变量"""
        if self.variables.parent:
            snapshot = self.variables.snapshot()
            self.variables = self.variables.parent
            return snapshot
        return self.variables.snapshot()

    def snapshot_variables(self) -> Dict[str, Any]:
        """获取所有变量快照"""
        return self.variables.snapshot()

    def merge_variables(self, variables: Dict[str, Any]) -> None:
        """合并变量"""
        self.variables.merge(variables)

    # ========== 状态管理 ==========

    def update_state(self, state: ExecutionState) -> None:
        """更新执行状态"""
        self.state = state

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self.state == ExecutionState.RUNNING

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.state == ExecutionState.COMPLETED

    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.state == ExecutionState.FAILED

    @property
    def is_cancelled(self) -> bool:
        """是否已取消"""
        return self.state == ExecutionState.CANCELLED

    # ========== 执行环境 ==========

    @property
    def is_main_world(self) -> bool:
        """是否是 MAIN 世界"""
        return self.world == "MAIN"

    @property
    def is_isolated_world(self) -> bool:
        """是否是 ISOLATED 世界"""
        return self.world == "ISOLATED"

    # ========== 元数据管理 ==========

    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)

    def has_metadata(self, key: str) -> bool:
        """检查元数据是否存在"""
        return key in self.metadata

    def remove_metadata(self, key: str) -> Any:
        """删除元数据"""
        return self.metadata.pop(key, None)

    # ========== 上下文传播 ==========

    def fork(self, **overrides) -> 'ExecutionContext':
        """创建上下文的副本（分支）"""
        return ExecutionContext(
            tab_id=overrides.get('tab_id', self.tab_id),
            world=overrides.get('world', self.world),
            timeout=overrides.get('timeout', self.timeout),
            retry_count=overrides.get('retry_count', self.retry_count),
            retry_delay=overrides.get('retry_delay', self.retry_delay),
            variables=self.variables,  # 共享变量作用域
            state=overrides.get('state', self.state),
            metadata={**self.metadata, **overrides.get('metadata', {})},
        )

    def clone(self) -> 'ExecutionContext':
        """克隆完整的上下文（独立变量作用域）"""
        return ExecutionContext(
            tab_id=self.tab_id,
            world=self.world,
            timeout=self.timeout,
            retry_count=self.retry_count,
            retry_delay=self.retry_delay,
            variables=VariableScope(
                variables=self.variables.snapshot(),
                parent=None,
            ),
            state=self.state,
            metadata={**self.metadata},
        )

    # ========== 工具方法 ==========

    def __repr__(self) -> str:
        return (
            f"ExecutionContext(tab_id={self.tab_id}, "
            f"world={self.world}, "
            f"state={self.state.value}, "
            f"variables={len(self.variables.snapshot())})"
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "tab_id": self.tab_id,
            "world": self.world,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "state": self.state.value,
            "variables": self.variables.snapshot(),
            "metadata": self.metadata,
        }


# ========== 流程上下文 ==========

class FlowContext:
    """
    流程执行上下文

    管理流程执行过程中的上下文信息，包括变量、步骤索引、调用栈等。
    """

    def __init__(self, initial_vars: Dict[str, Any] = None):
        self.root_scope = VariableScope()
        if initial_vars:
            self.root_scope.variables = {**initial_vars}
        self._current_scope = self.root_scope

        self.step_index = 0
        self.step_count = 0
        self.call_stack: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        self.result_data: Dict[str, Any] = {}
        self.error_info: Optional[Dict[str, Any]] = None

    @property
    def variables(self) -> VariableScope:
        """获取当前变量作用域"""
        return self._current_scope

    def push_scope(self, variables: Dict[str, Any] = None) -> None:
        """推入新的作用域"""
        new_scope = VariableScope(parent=self._current_scope)
        if variables:
            new_scope.variables = {**variables}
        self._current_scope = new_scope

    def pop_scope(self) -> Dict[str, Any]:
        """弹出作用域"""
        if self._current_scope.parent:
            snapshot = self._current_scope.snapshot()
            self._current_scope = self._current_scope.parent
            return snapshot
        return self._current_scope.snapshot()

    def push_call(self, flow_name: str, step_index: int) -> None:
        """推入函数调用"""
        self.call_stack.append({
            "flow_name": flow_name,
            "step_index": step_index,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def pop_call(self) -> Dict[str, Any]:
        """弹出函数调用"""
        if self.call_stack:
            return self.call_stack.pop()
        return {}

    @property
    def is_in_subflow(self) -> bool:
        """是否在子流程中"""
        return len(self.call_stack) > 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "step_index": self.step_index,
            "step_count": self.step_count,
            "call_stack_depth": len(self.call_stack),
            "variables_count": len(self._current_scope.snapshot()),
            "result_keys": list(self.result_data.keys()),
            "error": self.error_info,
        }


# ========== 便捷函数 ==========

def create_context(
    tab_id: int = None,
    world: str = "MAIN",
    timeout: int = 30000,
    variables: Dict[str, Any] = None,
) -> ExecutionContext:
    """创建执行上下文"""
    ctx = ExecutionContext(
        tab_id=tab_id,
        world=world,
        timeout=timeout,
    )
    if variables:
        ctx.merge_variables(variables)
    return ctx


__all__ = [
    "ExecutionContext",
    "ExecutionState",
    "VariableScope",
    "FlowContext",
    "create_context",
]
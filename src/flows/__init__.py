"""
流程引擎模块

提供流程定义、执行和管理功能。

主要组件:
- FlowEngine: 流程执行引擎
- FlowContext: 流程执行上下文
- FlowStep: 流程步骤基类
- FlowParser: 流程定义解析器

使用示例:
    ```python
    from flows import FlowEngine

    flow_data = {
        "name": "登录流程",
        "steps": [
            {
                "id": "step_1",
                "name": "打开登录页",
                "type": "action",
                "tool": "browser.navigate",
                "params": {"url": "https://example.com/login"}
            },
            {
                "id": "step_2",
                "name": "输入用户名",
                "type": "action",
                "tool": "browser.fill",
                "params": {"selector": "#username", "value": "${username}"}
            }
        ]
    }

    engine = FlowEngine()
    result = await engine.execute(flow_data, variables={"username": "test"})
    print(f"执行完成: {result.state}")
    ```
"""

from .context import FlowContext, FlowExecutionState
from .engine import FlowEngine, run_flow
from .steps import (
    FlowStep,
    StepType,
    StepStatus,
    StepConfig,
    StepResult,
    ActionStep,
    ConditionStep,
    LoopStep,
    WaitStep,
)
from .parsers import FlowParser, FlowValidator

__all__ = [
    # Context
    "FlowContext",
    "FlowExecutionState",
    # Engine
    "FlowEngine",
    "run_flow",
    # Steps
    "FlowStep",
    "StepType",
    "StepStatus",
    "StepConfig",
    "StepResult",
    "ActionStep",
    "ConditionStep",
    "LoopStep",
    "WaitStep",
    # Parsers
    "FlowParser",
    "FlowValidator",
]
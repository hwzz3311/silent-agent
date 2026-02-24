"""
执行相关 API 数据模型

提供工具调用和流程执行的数据模型。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field

from .common import ToolCall, ExecutionStatus


class ExecuteRequest(BaseModel):
    """执行请求"""
    tool: str = Field(..., min_length=1, description="工具名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    timeout: Optional[int] = Field(None, ge=1000, le=300000, description="超时时间（毫秒）")
    tab_id: Optional[int] = Field(None, description="标签页 ID")


class ExecuteResponse(BaseModel):
    """执行响应"""
    success: bool
    data: Optional[Any] = None
    error: Optional[Union[Dict[str, Any], str]] = None
    meta: Optional[Dict[str, Any]] = None


class BatchExecuteRequest(BaseModel):
    """批量执行请求"""
    calls: List[ToolCall] = Field(..., description="工具调用列表")
    continue_on_error: bool = Field(False, description="是否遇到错误时继续执行")
    parallel: bool = Field(False, description="是否并行执行")


class BatchExecuteResponse(BaseModel):
    """批量执行响应"""
    results: List[ExecuteResponse]
    success_count: int
    failure_count: int
    total_duration_ms: int


class FlowExecuteRequest(BaseModel):
    """流程执行请求"""
    flow_id: Optional[str] = Field(None, description="流程 ID")
    flow_data: Optional[Dict[str, Any]] = Field(None, description="流程数据（直接提供流程定义）")
    variables: Dict[str, Any] = Field(default_factory=dict, description="初始变量")
    timeout: Optional[int] = Field(None, ge=1000, le=600000, description="总超时时间（毫秒）")
    context: Optional[Dict[str, Any]] = Field(None, description="执行上下文")


class FlowExecuteResponse(BaseModel):
    """流程执行响应"""
    execution_id: str
    status: ExecutionStatus
    variables: Dict[str, Any] = Field(default_factory=dict)
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int
    started_at: datetime
    completed_at: Optional[datetime] = None


class ExecutionResult(BaseModel):
    """执行结果"""
    execution_id: str
    status: ExecutionStatus
    data: Optional[Any] = None
    error: Optional[Union[Dict[str, Any], str]] = None
    duration_ms: int


class ExecutionStepResult(BaseModel):
    """执行步骤结果"""
    step_id: str
    step_name: str
    tool: str
    status: ExecutionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: int
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Any] = None
    error: Optional[str] = None


class ExecutionLogResponse(BaseModel):
    """执行日志响应"""
    execution_id: str
    steps: List[ExecutionStepResult]
    screenshots: List[str] = Field(default_factory=list)


class ExecutionListResponse(BaseModel):
    """执行列表响应"""
    executions: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
"""
流程相关 API 数据模型

提供流程定义、创建、更新、列表等数据模型。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class FlowStepType(str, Enum):
    """流程步骤类型"""
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    PARALLEL_BRANCH = "parallel_branch"
    WAIT = "wait"
    SUB_FLOW = "sub_flow"
    SET_VAR = "set_var"
    LOG = "log"


class FlowVariableType(str, Enum):
    """流程变量类型"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class FlowStep(BaseModel):
    """流程步骤定义"""
    id: str
    name: str
    type: FlowStepType
    tool: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    condition: Optional[str] = None
    on_true: List['FlowStep'] = Field(default_factory=list)
    on_false: List['FlowStep'] = Field(default_factory=list)
    loop_config: Optional[Dict[str, Any]] = None
    parallel_branches: Optional[List[List['FlowStep']]] = None
    timeout: Optional[int] = None
    retry_count: int = 1
    retry_delay: int = 1000
    next_on_success: Optional[str] = None
    next_on_failure: Optional[str] = None


class FlowVariable(BaseModel):
    """流程变量定义"""
    name: str
    type: FlowVariableType
    description: Optional[str] = None
    default: Optional[Any] = None
    required: bool = False


class FlowCreateRequest(BaseModel):
    """流程创建请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    variables: List[FlowVariable] = Field(default_factory=list)
    steps: List[FlowStep] = Field(..., min_items=1)
    timeout: Optional[int] = Field(None, ge=1000, le=600000)
    tags: List[str] = Field(default_factory=list)


class FlowUpdateRequest(BaseModel):
    """流程更新请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    variables: Optional[List[FlowVariable]] = None
    steps: Optional[List[FlowStep]] = None
    timeout: Optional[int] = Field(None, ge=1000, le=600000)
    tags: Optional[List[str]] = None


class FlowResponse(BaseModel):
    """流程响应"""
    id: str
    name: str
    description: Optional[str]
    version: str
    category: Optional[str]
    tags: List[str]
    variables_count: int
    steps_count: int
    created_at: datetime
    updated_at: datetime


class FlowDetailResponse(BaseModel):
    """流程详情响应"""
    id: str
    name: str
    description: Optional[str]
    version: str
    category: Optional[str]
    tags: List[str]
    variables: List[FlowVariable]
    steps: List[Dict[str, Any]]
    timeout: Optional[int]
    created_at: datetime
    updated_at: datetime


class FlowListResponse(BaseModel):
    """流程列表响应"""
    flows: List[FlowResponse]
    total: int
    page: int
    page_size: int


class FlowRunResponse(BaseModel):
    """流程运行响应"""
    execution_id: str
    flow_id: str
    flow_name: str
    status: str
    variables: Dict[str, Any]
    current_step: Optional[str] = None
    started_at: datetime


class FlowTemplateResponse(BaseModel):
    """流程模板响应"""
    id: str
    name: str
    description: str
    category: str
    variables: List[str]
    steps_count: int


# 解决 Forward Reference 问题
FlowStep.model_rebuild()
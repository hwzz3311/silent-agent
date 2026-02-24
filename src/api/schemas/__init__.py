"""
API Schemas 模块

提供 API 请求和响应的数据模型定义。
"""

from .common import (
    ToolCall,
    ToolCallRequest,
    ToolCallResponse,
    ExecutionStatus,
    ErrorResponse,
    PaginationParams,
    PaginationResponse,
    HealthResponse,
    ServerInfo,
)

from .tools import (
    ToolListResponse,
    ToolDetailResponse,
    ToolSchemaResponse,
    ToolSearchResponse,
)

from .execute import (
    ExecuteRequest,
    ExecuteResponse,
    BatchExecuteRequest,
    BatchExecuteResponse,
    FlowExecuteRequest,
    FlowExecuteResponse,
    ExecutionResult,
    ExecutionStepResult,
)

from .flows import (
    FlowCreateRequest,
    FlowUpdateRequest,
    FlowResponse,
    FlowDetailResponse,
    FlowListResponse,
    FlowRunResponse,
)

from .record import (
    RecordStartResponse,
    RecordStopResponse,
    RecordDetailResponse,
    RecordListResponse,
    RecordingAction,
    ReplayRequest,
    ReplayResponse,
)

__all__ = [
    # Common
    "ToolCall",
    "ToolCallRequest",
    "ToolCallResponse",
    "ExecutionStatus",
    "ErrorResponse",
    "PaginationParams",
    "PaginationResponse",
    "HealthResponse",
    "ServerInfo",
    # Tools
    "ToolListResponse",
    "ToolDetailResponse",
    "ToolSchemaResponse",
    "ToolSearchResponse",
    # Execute
    "ExecuteRequest",
    "ExecuteResponse",
    "BatchExecuteRequest",
    "BatchExecuteResponse",
    "FlowExecuteRequest",
    "FlowExecuteResponse",
    "ExecutionResult",
    "ExecutionStepResult",
    # Flows
    "FlowCreateRequest",
    "FlowUpdateRequest",
    "FlowResponse",
    "FlowDetailResponse",
    "FlowListResponse",
    "FlowRunResponse",
    # Record
    "RecordStartResponse",
    "RecordStopResponse",
    "RecordDetailResponse",
    "RecordListResponse",
    "RecordingAction",
    "ReplayRequest",
    "ReplayResponse",
]
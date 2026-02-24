"""
API 模块

提供 Neurone RPA Server 的 API 接口。

包含:
- FastAPI 应用
- 工具相关接口 (tools)
- 执行相关接口 (execute)
- 流程相关接口 (flows)
"""

from .app import app, create_app
from .schemas import (
    # Common
    ToolCall,
    ToolCallRequest,
    ToolCallResponse,
    ExecutionStatus,
    ErrorResponse,
    PaginationParams,
    PaginationResponse,
    HealthResponse,
    ServerInfo,
    # Tools
    ToolListResponse,
    ToolDetailResponse,
    ToolSchemaResponse,
    # Execute
    ExecuteRequest,
    ExecuteResponse,
    FlowExecuteRequest,
    FlowExecuteResponse,
    ExecutionResult,
    ExecutionStepResult,
    # Flows
    FlowCreateRequest,
    FlowUpdateRequest,
    FlowResponse,
    FlowDetailResponse,
    FlowListResponse,
)

__all__ = [
    # App
    "app",
    "create_app",
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
    # Execute
    "ExecuteRequest",
    "ExecuteResponse",
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
]
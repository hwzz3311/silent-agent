"""
通用 API 数据模型

提供请求和响应的基础数据模型。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolCall(BaseModel):
    """工具调用信息"""
    name: str = Field(..., description="工具名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    name: str = Field(..., description="工具名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    timeout: Optional[int] = Field(None, ge=1000, le=300000, description="超时时间（毫秒）")


class ToolCallResponse(BaseModel):
    """工具调用响应"""
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误信息")
    details: Optional[Dict[str, Any]] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class PaginationResponse(BaseModel):
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    version: str
    extensions: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WebSocketMessage(BaseModel):
    """WebSocket 消息"""
    type: str = Field(..., description="消息类型")
    id: Optional[str] = Field(None, description="请求 ID")
    payload: Optional[Dict[str, Any]] = Field(None, description="消息载荷")


class ServerInfo(BaseModel):
    """服务器信息"""
    name: str = "Neurone RPA Server"
    version: str
    host: str
    port: int
    extensions: List[str] = Field(default_factory=list)
    tools_count: int = 0
    flows_count: int = 0
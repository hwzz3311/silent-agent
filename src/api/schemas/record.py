"""
录制回放相关 API 数据模型

提供录制开始/停止、回放等数据模型。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RecordStartResponse(BaseModel):
    """开始录制响应"""
    recording_id: str
    started_at: datetime
    tab_id: Optional[str] = None


class RecordStopResponse(BaseModel):
    """停止录制响应"""
    recording_id: str
    stopped_at: datetime
    actions_count: int
    duration_ms: int
    page_url: Optional[str] = None
    page_title: Optional[str] = None


class RecordingAction(BaseModel):
    """录制操作"""
    type: str = Field(..., description="操作类型")
    selector: Optional[str] = Field(None, description="元素选择器")
    value: Optional[str] = Field(None, description="输入值")
    x: Optional[int] = Field(None, description="X坐标")
    y: Optional[int] = Field(None, description="Y坐标")
    timestamp: float = Field(..., description="时间戳")
    duration: Optional[int] = Field(None, description="持续时间")


class RecordDetailResponse(BaseModel):
    """录制详情响应"""
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    duration_ms: int
    actions: List[RecordingAction]
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    tab_id: Optional[str] = None


class RecordListItem(BaseModel):
    """录制列表项"""
    id: str
    name: Optional[str] = None
    created_at: datetime
    duration_ms: int
    actions_count: int
    page_url: Optional[str] = None


class RecordListResponse(BaseModel):
    """录制列表响应"""
    recordings: List[RecordListItem]
    total: int
    page: int
    page_size: int


class ReplayRequest(BaseModel):
    """回放请求"""
    speed: float = Field(1.0, ge=0.1, le=10.0, description="回放速度")
    headless: bool = Field(False, description="是否 headless 模式执行")
    tab_id: Optional[int] = Field(None, description="指定标签页 ID")


class ReplayResponse(BaseModel):
    """回放响应"""
    execution_id: str
    recording_id: str
    status: str
    speed: float


class ReplayStatusResponse(BaseModel):
    """回放状态响应"""
    execution_id: str
    recording_id: str
    status: str
    current_action: Optional[int] = None
    total_actions: int
    progress: float = 0.0
    started_at: datetime
    completed_at: Optional[datetime] = None


class OptimizeResponse(BaseModel):
    """AI优化录制响应"""
    success: bool
    optimized_recording_id: str
    message: str
    changes: List[Dict[str, Any]] = Field(default_factory=list)
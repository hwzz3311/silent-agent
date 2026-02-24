"""
工具相关 API 数据模型

提供工具列表、详情、Schema 等数据模型。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .common import PaginationResponse


class ToolParameterProperty(BaseModel):
    """工具参数属性"""
    type: str
    description: Optional[str] = None
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None
    required: bool = False
    properties: Optional[Dict[str, Any]] = None
    items: Optional[Dict[str, Any]] = None


class ToolParameterSchema(BaseModel):
    """工具参数 Schema"""
    type: str = "object"
    properties: Dict[str, ToolParameterProperty] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ToolReturnsSchema(BaseModel):
    """工具返回值 Schema"""
    type: str = "object"
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class ToolInfoModel(BaseModel):
    """工具信息模型"""
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "utility"
    tags: List[str] = Field(default_factory=list)


class ToolMetadataModel(BaseModel):
    """工具元数据模型"""
    info: ToolInfoModel
    author: str = "unknown"
    license: str = "MIT"
    home_url: str = ""
    source_url: str = ""
    is_deprecated: bool = False
    replacement: Optional[str] = None


class ToolListResponse(BaseModel):
    """工具列表响应"""
    tools: List[str]
    count: int
    categories: Dict[str, int] = Field(default_factory=dict)
    tags: Dict[str, int] = Field(default_factory=dict)


class ToolDetailResponse(BaseModel):
    """工具详情响应"""
    name: str
    description: str
    version: str
    category: str
    tags: List[str]
    parameters: ToolParameterSchema
    returns: ToolReturnsSchema
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    is_deprecated: bool = False
    replacement: Optional[str] = None


class ToolSchemaResponse(BaseModel):
    """工具 Schema 响应"""
    name: str
    description: str
    version: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class ToolSearchResponse(BaseModel):
    """工具搜索响应"""
    query: str
    results: List[str]
    count: int
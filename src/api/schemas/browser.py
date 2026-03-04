"""
浏览器管理相关 API 数据模型

提供浏览器实例注册、查询、注销的数据模型。
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RegisterBrowserRequest(BaseModel):
    """注册浏览器实例请求"""
    mode: str = Field("hybrid", description="浏览器模式（extension/puppeteer/hybrid）")
    secret_key: Optional[str] = Field(None, description="扩展密钥")
    ws_endpoint: Optional[str] = Field(None, description="WebSocket 端点")
    relay_host: str = Field("127.0.0.1", description="Relay 服务器主机")
    relay_port: int = Field(18792, description="Relay 服务器端口")


class RegisterBrowserResponse(BaseModel):
    """注册浏览器实例响应"""
    instance_id: str
    mode: str
    is_default: bool


class BrowserInstanceInfo(BaseModel):
    """浏览器实例信息"""
    instance_id: str
    mode: str
    secret_key: Optional[str] = None
    ws_endpoint: Optional[str] = None
    relay_host: str
    relay_port: int
    is_connected: bool
    created_at: Optional[str] = None


class BrowserListResponse(BaseModel):
    """浏览器实例列表响应"""
    instances: List[BrowserInstanceInfo]
    total: int


class BrowserHealthResponse(BaseModel):
    """浏览器实例健康检查响应"""
    instance_id: str
    is_connected: bool
    mode: str


__all__ = [
    "RegisterBrowserRequest",
    "RegisterBrowserResponse",
    "BrowserInstanceInfo",
    "BrowserListResponse",
    "BrowserHealthResponse",
]

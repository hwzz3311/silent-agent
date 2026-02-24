"""
WebSocket 客户端模块

提供连接管理、消息发送接收等功能。
"""

from .client import SilentAgentClient, create_client
from .connection import ConnectionManager, ConnectionConfig, ConnectionInfo, ConnectionState
from .exceptions import (
    ClientException,
    ConnectionError,
    DisconnectedError,
    TimeoutError,
    ProtocolError,
    ExtensionNotConnectedError,
    ToolNotFoundError,
    ExecutionError,
    MessageParseError,
)

__all__ = [
    # Client
    "SilentAgentClient",
    "create_client",
    # Connection
    "ConnectionManager",
    "ConnectionConfig",
    "ConnectionInfo",
    "ConnectionState",
    # Exceptions
    "ClientException",
    "ConnectionError",
    "DisconnectedError",
    "TimeoutError",
    "ProtocolError",
    "ExtensionNotConnectedError",
    "ToolNotFoundError",
    "ExecutionError",
    "MessageParseError",
]
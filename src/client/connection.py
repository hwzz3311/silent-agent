"""
连接管理模块

提供 WebSocket 连接管理功能。
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

from .exceptions import (
    ConnectionError,
    DisconnectedError,
    TimeoutError,
    ProtocolError,
)


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionConfig:
    """连接配置"""
    host: str = "127.0.0.1"
    port: int = 18792
    path: str = "/controller"
    auto_reconnect: bool = True
    reconnect_delay: float = 5.0
    reconnect_max_attempts: int = 10
    heartbeat_interval: float = 30.0
    heartbeat_timeout: float = 10.0
    connection_timeout: float = 30.0

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}{self.path}"


@dataclass
class ConnectionInfo:
    """连接信息"""
    state: ConnectionState
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    reconnect_attempts: int = 0
    last_error: Optional[str] = None
    extension_connected: bool = False
    extension_tools: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
            "reconnect_attempts": self.reconnect_attempts,
            "last_error": self.last_error,
            "extension_connected": self.extension_connected,
            "extension_tools": self.extension_tools,
        }


class ConnectionManager:
    """
    WebSocket 连接管理器

    Attributes:
        config: 连接配置
        socket: WebSocket 连接
        state: 连接状态
        info: 连接信息
    """

    def __init__(self, config: ConnectionConfig = None):
        self.config = config or ConnectionConfig()
        self.socket = None
        self.state = ConnectionState.DISCONNECTED
        self.info = ConnectionInfo(state=ConnectionState.DISCONNECTED)

        # 内部状态
        self._lock = asyncio.Lock()
        self._listen_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._event_handlers: Dict[str, List[Callable]] = {}

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self.state == ConnectionState.CONNECTED

    @property
    def extension_tools(self) -> List[str]:
        """获取扩展工具列表"""
        return self.info.extension_tools

    @property
    def is_extension_connected(self) -> bool:
        """扩展是否已连接"""
        return self.info.extension_connected

    def on_event(self, event_type: str, handler: Callable) -> None:
        """注册事件处理器"""
        self._event_handlers.setdefault(event_type, []).append(handler)

    def off_event(self, event_type: str, handler: Callable) -> None:
        """取消注册事件处理器"""
        handlers = self._event_handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def connect(self) -> ConnectionInfo:
        """建立连接"""
        async with self._lock:
            if self.is_connected:
                return self.info

            try:
                self.state = ConnectionState.CONNECTING
                self.info = ConnectionInfo(
                    state=ConnectionState.CONNECTING,
                    last_error=None,
                )

                # 导入 websockets
                try:
                    import websockets
                except ImportError:
                    raise ConnectionError("请安装 websockets: pip install websockets")

                # 建立连接
                self.socket = await asyncio.wait_for(
                    websockets.connect(
                        self.config.url,
                        open_timeout=self.config.connection_timeout,
                    ),
                    timeout=self.config.connection_timeout,
                )

                # 更新状态
                self.state = ConnectionState.CONNECTED
                self.info.connected_at = datetime.utcnow()
                self.info.extension_connected = False

                logger.info(f"[ConnectionManager] 已连接到: {self.config.url}")

                # 启动监听任务
                self._listen_task = asyncio.create_task(self._listen())

                # 启动心跳任务
                self._heartbeat_task = asyncio.create_task(self._heartbeat())

                # 触发连接事件
                self._emit_event("connected", {"url": self.config.url})

                return self.info

            except asyncio.TimeoutError:
                self.state = ConnectionState.FAILED
                self.info.last_error = "连接超时"
                logger.error("[ConnectionManager] 连接超时")
                raise ConnectionError("连接超时", {"timeout": self.config.connection_timeout})

            except Exception as e:
                self.state = ConnectionState.FAILED
                self.info.last_error = str(e)
                logger.error(f"[ConnectionManager] 连接失败: {e}")
                raise ConnectionError(f"连接失败: {e}")

    async def disconnect(self, reason: str = "用户断开") -> None:
        """断开连接"""
        async with self._lock:
            if not self.is_connected:
                return

            logger.info(f"[ConnectionManager] 断开连接: {reason}")

            # 取消任务
            self._cancel_task(self._listen_task)
            self._cancel_task(self._heartbeat_task)

            # 关闭 socket
            if self.socket:
                try:
                    await self.socket.close()
                except Exception as e:
                    logger.warning(f"[ConnectionManager] 关闭 socket 失败: {e}")
                self.socket = None

            # 更新状态
            self.state = ConnectionState.DISCONNECTED
            self.info.disconnected_at = datetime.utcnow()
            self.info.extension_connected = False
            self.info.extension_tools = []

            # 触发断开事件
            self._emit_event("disconnected", {"reason": reason})

    async def reconnect(self, max_attempts: int = None) -> ConnectionInfo:
        """重新连接"""
        await self.disconnect("重新连接")

        attempts = 0
        max_attempts = max_attempts or self.config.reconnect_max_attempts

        while attempts < max_attempts:
            try:
                attempts += 1
                self.info.reconnect_attempts = attempts
                self.state = ConnectionState.RECONNECTING
                logger.info(f"[ConnectionManager] 重新连接 (第 {attempts}/{max_attempts} 次)...")

                await asyncio.sleep(self.config.reconnect_delay)
                return await self.connect()

            except ConnectionError:
                continue

        self.state = ConnectionState.FAILED
        self.info.last_error = "重新连接失败"
        raise ConnectionError("重新连接失败", {"attempts": attempts})

    async def send(self, message: dict) -> None:
        """发送消息"""
        if not self.is_connected:
            raise DisconnectedError("未连接到服务器")

        try:
            await self.socket.send(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"[ConnectionManager] 发送消息失败: {e}")
            # 更新连接状态
            self.state = ConnectionState.DISCONNECTED
            raise ConnectionError(f"发送消息失败: {e}")

    async def send_and_wait(
        self,
        message: dict,
        timeout: float = 60.0,
        retry_on_disconnect: bool = True
    ) -> dict:
        """发送消息并等待响应"""
        if not self.is_connected:
            if retry_on_disconnect and self.config.auto_reconnect:
                # 尝试重连
                logger.warning("[ConnectionManager] 连接已断开，尝试重连...")
                try:
                    await self.reconnect()
                except Exception as e:
                    logger.error(f"[ConnectionManager] 重连失败: {e}")
                    raise DisconnectedError(f"未连接到服务器，重连也失败: {e}")
            else:
                raise DisconnectedError("未连接到服务器")

        # 生成请求 ID
        import uuid
        request_id = str(uuid.uuid4())

        # 创建 future 等待响应
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_responses[request_id] = future

        # 发送消息
        message["id"] = request_id
        try:
            await self.send(message)
        except ConnectionError as e:
            # 发送失败，尝试重连后重试
            if retry_on_disconnect and self.config.auto_reconnect:
                logger.warning(f"[ConnectionManager] 发送消息失败，尝试重连: {e}")
                try:
                    await self.reconnect()
                    # 重新创建 future
                    future = loop.create_future()
                    self._pending_responses[request_id] = future
                    await self.send(message)
                except Exception as re:
                    self._pending_responses.pop(request_id, None)
                    raise DisconnectedError(f"发送消息失败，重连后也失败: {re}")
            else:
                self._pending_responses.pop(request_id, None)
                raise

        # 等待响应
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_responses.pop(request_id, None)
            raise TimeoutError(f"等待响应超时: {request_id}", {"request_id": request_id})

    # ========== 内部方法 ==========

    def _cancel_task(self, task: asyncio.Task) -> None:
        """取消任务"""
        if task:
            task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(task)
            except asyncio.CancelledError:
                pass

    async def _listen(self) -> None:
        """监听消息"""
        try:
            async for raw_message in self.socket:
                await self._handle_message(raw_message)
        except asyncio.CancelledError:
            logger.info("[ConnectionManager] 监听任务已取消")
        except Exception as e:
            logger.error(f"[ConnectionManager] 监听错误: {e}")
            await self._handle_error(e)

    async def _handle_message(self, raw: str) -> None:
        """处理接收到的消息"""
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"[ConnectionManager] 消息解析失败: {e}")
            return

        # 响应消息 - 支持有/无 type 字段的情况
        if "id" in message and ("result" in message or message.get("type") in ("tool_result", "result")):
            future = self._pending_responses.pop(message["id"], None)
            if future and not future.done():
                if "error" in message:
                    future.set_exception(
                        ProtocolError(message.get("error"))
                    )
                else:
                    future.set_result(message.get("result"))
            return

        # 事件消息
        if message.get("type") == "event" or message.get("method") == "event":
            params = message.get("params", message.get("data", {}))
            self._handle_event(params)

    def _handle_event(self, params: dict) -> None:
        """处理事件"""
        event_type = params.get("type") or params.get("event")
        if not event_type:
            return

        # 更新扩展连接状态
        if event_type in ("extension_connected", "extension_disconnected"):
            self.info.extension_connected = event_type == "extension_connected"
            self.info.extension_tools = params.get("tools", [])

        # 触发事件处理器
        self._emit_event(event_type, params)

    def _emit_event(self, event_type: str, data: dict) -> None:
        """触发事件"""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(data))
                else:
                    handler(data)
            except Exception as e:
                logger.warning(f"[ConnectionManager] 事件处理器错误: {e}")

    async def _heartbeat(self) -> None:
        """心跳任务"""
        try:
            while self.is_connected:
                await asyncio.sleep(self.config.heartbeat_interval)
                try:
                    await self.send({"type": "ping"})
                except Exception as e:
                    logger.warning(f"[ConnectionManager] 心跳发送失败: {e}")
                    break
        except asyncio.CancelledError:
            pass

    async def _handle_error(self, error: Exception) -> None:
        """处理错误"""
        self.info.last_error = str(error)
        self._emit_event("error", {"error": str(error)})

        if self.config.auto_reconnect:
            try:
                await self.reconnect()
            except ConnectionError:
                pass

    # ========== 响应管理 ==========

    @property
    def _pending_responses(self) -> dict:
        """获取待响应字典"""
        if not hasattr(self, "_pending_responses_dict"):
            self._pending_responses_dict = {}
        return self._pending_responses_dict

    async def close(self) -> None:
        """关闭连接管理器"""
        await self.disconnect("关闭连接管理器")
        self._event_handlers.clear()


__all__ = [
    "ConnectionManager",
    "ConnectionConfig",
    "ConnectionInfo",
    "ConnectionState",
]
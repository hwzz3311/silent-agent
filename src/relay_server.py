#!/usr/bin/env python3
"""
Neurone Relay Server v2 — WebSocket Relay 服务器

作为 Chrome 扩展与 Python 控制器之间的桥梁:
- /extension  — 扩展 WebSocket（接收 HELLO / TOOL_RESULT / PONG）
- /controller — 控制器 WebSocket（发送 executeTool / listTools / getStatus）
- /health-check — 探测服务器是否存活

协议：
  扩展 → Relay:  { type:"hello", extensionId, version, tools:[...] }
  扩展 → Relay:  { type:"tool_result", requestId, result }
  扩展 → Relay:  { type:"pong" }
  Relay → 扩展:  { type:"tool_call", requestId, payload:{ name, args } }
  Relay → 扩展:  { type:"ping" }

  控制器 → Relay: { id, method:"executeTool", params:{ name, args } }
  控制器 → Relay: { id, method:"listTools" }
  控制器 → Relay: { id, method:"getStatus" }
  Relay → 控制器: { id, result } | { id, error }
  Relay → 控制器: { method:"event", params:{ type, ... } }

使用:
    python relay_server.py --port 18792
"""

import asyncio
import json
import logging
import argparse
import uuid
import signal
from datetime import datetime
from typing import Dict, Set, Any, Optional
from dataclasses import dataclass, field

try:
    import websockets
    from websockets.asyncio.server import ServerConnection
    from websockets.http11 import Response, Request
    from websockets.datastructures import Headers
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("请安装 websockets: pip install 'websockets>=14.0'")
    exit(1)


class HeadTolerantConnection(ServerConnection):
    """静默处理 HEAD 等非 GET 请求（Chrome 内部可达性探测）"""
    async def handshake(self, *args, **kwargs):
        try:
            await super().handshake(*args, **kwargs)
        except Exception as exc:
            cause = getattr(exc, '__cause__', None)
            if cause and 'unsupported HTTP method' in str(cause):
                return
            raise


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


# ==================== 状态 ====================

@dataclass
class ExtensionInfo:
    """扩展连接信息（用于多插件路由）"""
    ws: ServerConnection
    extension_id: str
    version: str
    tools: list
    secret_key: str
    connected_at: datetime = None


@dataclass
class RelayState:
    """
    Relay 服务器状态

    支持多插件连接：
    - extensions: Dict[str, ExtensionInfo] - 按密钥存储多个扩展连接
      key: 插件密钥 (secretKey)
      value: 扩展连接信息
    """
    # 多插件支持：key -> ExtensionInfo
    extensions: Dict[str, ExtensionInfo] = field(default_factory=dict)
    controller_connections: Set[ServerConnection] = field(default_factory=set)
    # requestId -> (key, asyncio.Future)  (等待扩展返回 TOOL_RESULT, 关联密钥)
    pending_tool_calls: Dict[str, tuple] = field(default_factory=dict)
    # 连接时间追踪（用于避免重复日志）
    last_extension_connect_time: float = 0.0
    last_extension_id: Optional[str] = None


state = RelayState()


# ---------- 连接日志去重 ----------
def _should_log_connection(extension_id: str) -> bool:
    """判断是否应该输出连接日志（避免 Service Worker 频繁重连刷屏）"""
    import time
    current_time = time.time()

    # 如果是同一个扩展在 5 秒内重连，静默处理
    if (extension_id == state.last_extension_id and
        current_time - state.last_extension_connect_time < 5):
        return False

    # 更新连接时间
    state.last_extension_connect_time = current_time
    state.last_extension_id = extension_id
    return True


# ==================== 服务器 ====================

class NeuroneRelayServer:
    def __init__(self, host="127.0.0.1", port=18792):
        self.host = host
        self.port = port
        self._server = None
        self._ping_task = None

    async def start(self):
        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            process_request=self._process_http,
            create_connection=HeadTolerantConnection,
            ping_interval=20,
            ping_timeout=60,
        )
        self._ping_task = asyncio.create_task(self._ping_loop())
        logger.info("🧠 Neurone Relay Server v2 已启动")
        logger.info(f"   HTTP:  http://{self.host}:{self.port}/")
        logger.info(f"   扩展:  ws://{self.host}:{self.port}/extension")
        logger.info(f"   控制器: ws://{self.host}:{self.port}/controller")

    async def stop(self):
        if self._ping_task:
            self._ping_task.cancel()
            try: await self._ping_task
            except asyncio.CancelledError: pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("Relay Server 已停止")

    # ---------- HTTP ----------

    def _process_http(self, connection, request: Request):
        if request.path in ("/", "/health"):
            return Response(200, "OK",
                            Headers([("Content-Type", "text/plain"),
                                     ("Access-Control-Allow-Origin", "*")]),
                            b"OK")
        return None

    # ---------- WebSocket 路由 ----------

    async def _handle_connection(self, ws: ServerConnection):
        path = ws.request.path
        remote = ws.remote_address
        logger.info(f"连接: path={path}  remote={remote}")

        # 添加更详细的日志来调试
        logger.info(f"WebSocket 请求: path={path}, subprotocols={ws.subprotocol}")

        if path == "/extension":
            await self._handle_extension(ws)
        elif path == "/controller":
            await self._handle_controller(ws)
        elif path == "/health-check":
            await ws.close(1000, "OK")
        else:
            await ws.close(1008, "Invalid path")

    # ---------- 扩展连接 ----------

    async def _handle_extension(self, ws):
        """
        处理插件连接（支持多密钥）

        插件通过 HELLO 消息携带 secretKey 进行身份识别
        同一密钥的插件可以替换旧连接
        """
        logger.info(">>> 进入 _handle_extension 处理")

        # 用于临时存储当前连接的密钥，等待 HELLO 消息
        current_key = None

        try:
            async for message in ws:
                # 解析消息获取密钥
                try:
                    msg_data = json.loads(message)
                except json.JSONDecodeError:
                    continue

                # HELLO 消息：获取密钥并注册连接
                if msg_data.get("type") == "hello":
                    secret_key = msg_data.get("secretKey", "")
                    current_key = secret_key

                    # 检查密钥是否已存在
                    if secret_key in state.extensions:
                        old_ext = state.extensions[secret_key]
                        logger.warning(f"⚠ 密钥 {secret_key[:8]}... 已存在，替换旧连接")
                        try:
                            await old_ext.ws.close()
                        except:
                            pass

                    # 注册新连接
                    ext_info = ExtensionInfo(
                        ws=ws,
                        extension_id=msg_data.get("extensionId", ""),
                        version=msg_data.get("version", ""),
                        tools=msg_data.get("tools", []),
                        secret_key=secret_key,
                        connected_at=datetime.utcnow()
                    )
                    state.extensions[secret_key] = ext_info

                    # 发送密钥验证响应
                    await ws.send(json.dumps({
                        "type": "hello_ack",
                        "keyAccepted": True,
                        "secretKey": secret_key
                    }))

                    logger.info(f"✓ 插件已连接: key={secret_key[:8]}... "
                                f"id={ext_info.extension_id} v={ext_info.version}")

                    # 广播事件到控制器
                    await self._broadcast_event("extension_connected", {
                        "extensionId": ext_info.extension_id,
                        "version": ext_info.version,
                        "tools": ext_info.tools,
                        "secretKey": secret_key,
                    })
                    continue

                # 其他消息：按密钥路由
                if current_key and current_key in state.extensions:
                    await self._on_extension_msg(message, current_key)

        except ConnectionClosed as e:
            logger.info(f"插件断开: key={current_key[:8] if current_key else '?'}... code={e.code}")
        except Exception as e:
            logger.error(f"插件异常: {e}")
        finally:
            # 清理当前密钥的连接
            if current_key and current_key in state.extensions:
                if state.extensions[current_key].ws is ws:
                    del state.extensions[current_key]
                    logger.info(f"✓ 插件连接已清理: key={current_key[:8]}...")

            # 广播断开事件
            await self._broadcast_event("extension_disconnected", {
                "secretKey": current_key
            })

    async def _on_extension_msg(self, raw, secret_key: str = None):
        """
        处理插件消息

        Args:
            raw: 原始消息
            secret_key: 插件密钥（可选，用于定位扩展）
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        # 如果未指定密钥，从消息中提取
        if not secret_key:
            secret_key = data.get("secretKey")

        msg_type = data.get("type", "")

        # PONG（心跳响应）
        if msg_type == "pong":
            return

        # TOOL_RESULT：完成工具调用
        if msg_type == "tool_result":
            req_id = str(data.get("requestId", ""))
            # 从 pending 中获取密钥和 future
            pending = state.pending_tool_calls.pop(req_id, None)
            if pending:
                key, fut = pending
                if fut and not fut.done():
                    if "error" in data:
                        fut.set_exception(Exception(data.get("error")))
                    else:
                        fut.set_result(data.get("result"))
            return

    # ---------- 控制器连接 ----------

    async def _handle_controller(self, ws):
        state.controller_connections.add(ws)
        logger.info(f"✓ 控制器已连接 (总数: {len(state.controller_connections)})")

        # 发送当前状态（支持多插件）
        connected_keys = list(state.extensions.keys())
        await ws.send(json.dumps({
            "method": "event",
            "params": {
                "type": "status",
                "extensionConnected": len(state.extensions) > 0,
                "extensionKeys": connected_keys,  # 已连接的密钥列表
                "extensions": {
                    key: {
                        "extensionId": ext.extension_id,
                        "version": ext.version,
                        "tools": ext.tools
                    }
                    for key, ext in state.extensions.items()
                }
            }
        }))

        try:
            async for message in ws:
                await self._on_controller_msg(ws, message)
        except ConnectionClosed:
            pass
        finally:
            state.controller_connections.discard(ws)
            logger.info(f"控制器断开 (剩余: {len(state.controller_connections)})")

    async def _on_controller_msg(self, ws, raw):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await ws.send(json.dumps({"error": "无效 JSON"}))
            return

        msg_id = data.get("id")
        method = data.get("method", "")
        params = data.get("params", {})

        try:
            if method == "executeTool":
                result = await self.execute_tool(
                    params.get("name"),
                    params.get("args", {}),
                    timeout=params.get("timeout", 60),
                    secret_key=params.get("secretKey"),  # 传递密钥用于多插件路由
                )
                await ws.send(json.dumps({"id": msg_id, "result": result}))

            elif method == "listTools":
                # 获取所有已连接插件的工具列表
                all_tools = set()
                for ext in state.extensions.values():
                    all_tools.update(ext.tools)
                await ws.send(json.dumps({
                    "id": msg_id,
                    "result": {
                        "tools": list(all_tools),
                        "extensionConnected": len(state.extensions) > 0,
                        "extensionKeys": list(state.extensions.keys()),  # 已连接密钥列表
                    }
                }))

            elif method == "getStatus":
                # 返回多插件状态
                await ws.send(json.dumps({
                    "id": msg_id,
                    "result": {
                        "extensionConnected": len(state.extensions) > 0,
                        # 返回所有已连接插件的详细信息
                        "extensions": {
                            key: {
                                "extensionId": ext.extension_id,
                                "version": ext.version,
                                "tools": ext.tools,
                                "connectedAt": ext.connected_at.isoformat() if ext.connected_at else None,
                            }
                            for key, ext in state.extensions.items()
                        },
                        "extensionKeys": list(state.extensions.keys()),
                    }
                }))

            else:
                await ws.send(json.dumps({"id": msg_id, "error": f"未知方法: {method}"}))

        except Exception as e:
            await ws.send(json.dumps({"id": msg_id, "error": str(e)}))

    # ---------- 工具调用 ----------

    async def execute_tool(
        self,
        name: str,
        args: dict = None,
        timeout: float = 60,
        secret_key: str = None
    ) -> Any:
        """
        向扩展发送 TOOL_CALL 并等待 TOOL_RESULT

        Args:
            name: 工具名称
            args: 工具参数
            timeout: 超时时间
            secret_key: 目标插件密钥（可选，不指定则发送到第一个连接的插件）

        Returns:
            工具执行结果
        """
        # 根据密钥获取目标插件
        if secret_key:
            if secret_key not in state.extensions:
                raise Exception(f"插件未连接: key={secret_key[:8]}...")
            target_ws = state.extensions[secret_key].ws
        else:
            # 无密钥时使用第一个连接的插件（向后兼容）
            if not state.extensions:
                raise Exception("没有已连接的插件")
            # 取第一个插件
            first_key = next(iter(state.extensions.keys()))
            target_ws = state.extensions[first_key].ws
            secret_key = first_key

        if not name:
            raise Exception("工具名称不能为空")

        request_id = str(uuid.uuid4())[:8]
        future = asyncio.get_event_loop().create_future()
        # 存储密钥和 future 的元组
        state.pending_tool_calls[request_id] = (secret_key, future)

        # 消息中携带密钥用于验证
        payload = {
            "type": "tool_call",
            "requestId": request_id,
            "secretKey": secret_key,  # 携带密钥用于插件验证
            "payload": {
                "name": name,
                "args": args or {},
            }
        }

        try:
            await target_ws.send(json.dumps(payload))
            logger.info(f"  → TOOL_CALL: {name}  id={request_id}  key={secret_key[:8]}...")
            raw_result = await asyncio.wait_for(future, timeout=timeout)
            logger.info(f"  ← TOOL_RESULT: {name}  id={request_id}")
            # 添加调试日志
            logger.info(f"  DEBUG raw_result: {raw_result}")

            # 转换扩展结果格式为标准 API 格式
            # 扩展返回: {content: [...], isError: ...}
            # API 期望: {success: bool, data: ..., error: ...}
            is_error = raw_result.get("isError", False)
            content = raw_result.get("content", [])

            if is_error:
                error_text = ""
                if content and isinstance(content, list):
                    error_items = [c.get("text", "") for c in content if c.get("type") == "error"]
                    error_text = " | ".join(error_items)
                return {
                    "success": False,
                    "error": error_text or "工具执行失败",
                    "data": None,
                }
            else:
                # 提取成功数据
                data_text = ""
                if content and isinstance(content, list):
                    data_items = [c.get("text", "") for c in content if c.get("type") != "error"]
                    data_text = " | ".join(data_items)
                # 尝试将 JSON 字符串解析为对象
                result_data = data_text
                if data_text:
                    try:
                        result_data = json.loads(data_text)
                    except (json.JSONDecodeError, ValueError):
                        # 不是 JSON，保持原字符串
                        pass
                return {
                    "success": True,
                    "data": result_data or raw_result.get("data"),
                    "error": None,
                }
        except asyncio.TimeoutError:
            state.pending_tool_calls.pop(request_id, None)
            raise Exception(f"工具调用超时: {name} ({timeout}s)")
        except Exception:
            state.pending_tool_calls.pop(request_id, None)
            raise

    # ---------- 广播 / 心跳 ----------

    async def _broadcast_event(self, event_type: str, params: dict):
        msg = json.dumps({"method": "event", "params": {"type": event_type, **params}})
        for ws in list(state.controller_connections):
            try:
                await ws.send(msg)
            except ConnectionClosed:
                state.controller_connections.discard(ws)

    async def _ping_loop(self):
        while True:
            await asyncio.sleep(30)
            if state.extension_ws:
                try:
                    await state.extension_ws.send(json.dumps({"type": "ping"}))
                except ConnectionClosed:
                    pass


# ==================== 便捷 API ====================

_server: Optional[NeuroneRelayServer] = None


async def start_relay(host="127.0.0.1", port=18792) -> NeuroneRelayServer:
    """启动 Relay 服务器"""
    global _server
    _server = NeuroneRelayServer(host, port)
    await _server.start()
    return _server


async def call_tool(name: str, args: dict = None, timeout: float = 60) -> Any:
    """
    调用浏览器工具

    Args:
        name: 工具名称，如 "chrome_navigate", "chrome_click" 等
        args: 工具参数
        timeout: 超时秒数

    Returns:
        工具执行结果

    Example:
        result = await call_tool("chrome_navigate", {"url": "https://www.baidu.com"})
        result = await call_tool("chrome_click", {"selector": "#su"})
        result = await call_tool("chrome_extract_data", {"selector": "title", "attribute": "text"})
    """
    if not _server:
        raise Exception("Relay 服务器未启动")
    return await _server.execute_tool(name, args, timeout)


def get_tools() -> list:
    """获取扩展注册的工具列表"""
    return list(state.extension_tools)


def is_extension_connected() -> bool:
    """扩展是否已连接"""
    return state.extension_ws is not None


# ==================== 主程序 ====================

async def main():
    parser = argparse.ArgumentParser(description="Neurone Relay Server v2")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18792)
    args = parser.parse_args()

    server = await start_relay(args.host, args.port)

    stop = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    print("\n按 Ctrl+C 停止服务器...\n")
    try:
        await stop.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())

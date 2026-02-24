"""
Neurone CDP Client - Asynchronous Chrome DevTools Protocol Client

使用 websockets 库实现与 Chrome CDP 端口的异步通信。
"""

import asyncio
import json
import uuid
from typing import Any, Dict, Optional
import websockets


class CDPClient:
    """
    Chrome DevTools Protocol 异步客户端

    用法:
        async with CDPClient() as client:
            dom = await client.get_dom()
            await client.click(100, 200)
    """

    def __init__(self, host: str = "localhost", port: int = 9222):
        self.host = host
        self.port = port
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.base_url = f"ws://{host}:{port}"
        self._response_futures: Dict[str, asyncio.Future] = {}

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self) -> None:
        """连接到 Chrome CDP WebSocket"""
        self.ws = await websockets.connect(self.base_url)

        # 启动消息监听循环
        asyncio.create_task(self._listen())

        # 启用必要的域
        await self.send_command("DOM.enable")
        await self.send_command("Input.enable")

    async def _listen(self) -> None:
        """监听来自 CDP 的消息（响应和事件）"""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                data = json.loads(message)

                # 检查是否是某个请求的响应
                if "id" in data:
                    msg_id = str(data["id"])
                    if msg_id in self._response_futures:
                        future = self._response_futures.pop(msg_id)
                        if "error" in data:
                            future.set_exception(Exception(data["error"]["message"]))
                        else:
                            future.set_result(data.get("result", {}))
        except Exception as e:
            print(f"CDP listen error: {e}")

    async def send_command(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        发送 CDP 命令并等待响应

        Args:
            method: CDP 方法名，如 "DOM.getDocument"
            params: 方法参数

        Returns:
            命令响应结果
        """
        if not self.ws:
            raise ConnectionError("Not connected to CDP")

        msg_id = str(uuid.uuid4())
        message = {
            "id": msg_id,
            "method": method,
            "params": params or {}
        }

        # 创建 Future 等待响应
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._response_futures[msg_id] = future

        # 发送消息
        await self.ws.send(json.dumps(message))

        # 等待响应
        return await future

    async def get_dom(self) -> Dict[str, Any]:
        """获取当前页面的 DOM 树"""
        result = await self.send_command("DOM.getDocument")
        return result.get("root", {})

    async def click(self, x: int, y: int, human: bool = True) -> Dict[str, Any]:
        """
        在指定坐标执行点击操作

        Args:
            x: X 坐标
            y: Y 坐标
            human: 是否模拟人类轨迹（默认 True）
        """
        if human:
            return await self._human_click(x, y)
        else:
            return await self._direct_click(x, y)

    async def _direct_click(self, x: int, y: int) -> Dict[str, Any]:
        """直接点击（无轨迹）"""
        result = await self.send_command("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1
        })
        await self.send_command("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": "left"
        })
        return result

    async def _human_click(self, x: int, y: int) -> Dict[str, Any]:
        """模拟人类轨迹的点击（带移动过程）"""
        import random

        # 生成轨迹点（从当前位置开始，添加随机偏移）
        points = [(x + random.randint(-5, 5), y + random.randint(-5, 5))]

        # 中间过渡点
        num_mid_points = random.randint(3, 7)
        for i in range(num_mid_points):
            t = (i + 1) / (num_mid_points + 1)
            px = int(x * t + random.randint(-20, 20))
            py = int(y * t + random.randint(-20, 20))
            points.append((px, py))

        points.append((x, y))

        # 移动鼠标
        for px, py in points:
            await self.send_command("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": px,
                "y": py
            })
            await asyncio.sleep(random.uniform(0.01, 0.03))

        # 按下
        await self.send_command("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": "left",
            "clickCount": 1
        })
        await asyncio.sleep(random.uniform(0.05, 0.1))

        # 释放
        await self.send_command("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": "left"
        })

        return {"success": True, "type": "human_click", "target": (x, y)}

    async def type_text(self, text: str) -> Dict[str, Any]:
        """在焦点位置输入文本"""
        result = await self.send_command("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "text": text
        })
        return result

    async def scroll(self, x: int, y: int, delta_x: int = 0, delta_y: int = 100) -> Dict[str, Any]:
        """滚动页面"""
        return await self.send_command("Input.dispatchMouseEvent", {
            "type": "mouseWheel",
            "x": x,
            "y": y,
            "deltaX": delta_x,
            "deltaY": delta_y
        })

    async def close(self) -> None:
        """关闭 CDP 连接"""
        if self.ws:
            await self.ws.close()
            self.ws = None
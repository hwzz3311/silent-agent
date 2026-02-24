#!/usr/bin/env python3
"""
Neurone Relay Client v2 — 通过工具调用控制浏览器

使用示例:
    async with SilentAgentClient() as client:
        # 查看可用工具
        tools = await client.list_tools()
        print(tools)

        # 导航到网页
        await client.navigate("https://www.baidu.com")

        # 提取数据
        title = await client.extract("title", attribute="text")
        print(title)

        # 点击
        await client.click("#su")

        # 填充表单
        await client.fill("#kw", "hello world")

        # 通用工具调用
        result = await client.call_tool("inject_script", code="return document.title")
"""

import asyncio
import json
from typing import Any, Dict, Optional, List, Callable

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("请安装 websockets: pip install websockets")
    exit(1)


class SilentAgentClient:
    """
    Neurone 控制器客户端

    通过 Relay 服务器远程调用浏览器扩展中的工具。

    用法:
        async with SilentAgentClient() as client:
            await client.navigate("https://example.com")
            title = await client.extract("title")
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 18792):
        self.host = host
        self.port = port
        self.ws = None
        self._next_id = 1
        self._pending: Dict[int, asyncio.Future] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._listen_task: Optional[asyncio.Task] = None
        self._extension_connected = False
        self._extension_tools: list = []

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def connect(self):
        """连接到 Relay 服务器"""
        url = f"ws://{self.host}:{self.port}/controller"
        self.ws = await websockets.connect(url)
        self._listen_task = asyncio.create_task(self._listen())

    async def close(self):
        """关闭连接"""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()
            self.ws = None

    # ==================== 底层通信 ====================

    async def _listen(self):
        try:
            async for message in self.ws:
                await self._on_message(message)
        except (ConnectionClosed, asyncio.CancelledError):
            pass

    async def _on_message(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        # 响应
        if "id" in data and ("result" in data or "error" in data):
            msg_id = data["id"]
            fut = self._pending.pop(msg_id, None)
            if fut and not fut.done():
                if "error" in data:
                    fut.set_exception(Exception(data["error"]))
                else:
                    fut.set_result(data.get("result"))
            return

        # 事件
        if data.get("method") == "event":
            params = data.get("params", {})
            event_type = params.get("type", "")

            if event_type == "status":
                self._extension_connected = params.get("extensionConnected", False)
                self._extension_tools = params.get("tools", [])

            elif event_type == "extension_connected":
                self._extension_connected = True
                self._extension_tools = params.get("tools", [])

            elif event_type == "extension_disconnected":
                self._extension_connected = False
                self._extension_tools = []

            # 调用注册的处理器
            for handler in self._event_handlers.get(event_type, []):
                try:
                    result = handler(params)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"[SilentAgentClient] 事件处理器错误: {e}")

    async def _send_request(self, method: str, params: dict = None, timeout: float = 60) -> Any:
        """发送请求并等待响应"""
        if not self.ws:
            raise Exception("未连接到 Relay 服务器")

        msg_id = self._next_id
        self._next_id += 1

        fut = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = fut

        await self.ws.send(json.dumps({
            "id": msg_id,
            "method": method,
            "params": params or {},
        }))

        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(msg_id, None)
            raise Exception(f"请求超时: {method}")

    # ==================== 通用 API ====================

    async def call_tool(self, name: str, timeout: float = 60, **args) -> Any:
        """
        调用浏览器工具

        Args:
            name: 工具名称
            timeout: 超时秒数
            **args: 工具参数

        Returns:
            工具执行结果

        Example:
            result = await client.call_tool("chrome_navigate", url="https://example.com")
        """
        # 记录调用日志
        print(f"[SilentAgentClient.call_tool] 开始调用工具: name={name}, args.keys={list(args.keys())}")
        if name == "inject_script":
            print(f"[SilentAgentClient.call_tool] inject_script code 长度: {len(args.get('code', ''))}")

        try:
            result = await self._send_request("executeTool", {
                "name": name,
                "args": args,
                "timeout": timeout,
            }, timeout=timeout + 5)

            print(f"[SilentAgentClient.call_tool] 工具调用成功: name={name}")
            return result
        except Exception as e:
            print(f"[SilentAgentClient.call_tool] 工具调用失败: name={name}, error={e}")
            raise

    async def list_tools(self) -> dict:
        """获取可用工具列表"""
        return await self._send_request("listTools")

    async def get_status(self) -> dict:
        """获取扩展连接状态"""
        return await self._send_request("getStatus")

    def on_event(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self._event_handlers.setdefault(event_type, []).append(handler)

    @property
    def is_extension_connected(self) -> bool:
        return self._extension_connected

    @property
    def tools(self) -> list:
        return list(self._extension_tools)

    # ==================== 便捷方法 ====================

    async def navigate(self, url: str, new_tab: bool = True, timeout: float = 30) -> dict:
        """导航到 URL"""
        return await self.call_tool("chrome_navigate", url=url, newTab=new_tab, timeout=timeout)

    async def click(self, selector: str, text: str = None, timeout: float = 5, wait_for_nav: bool = False) -> dict:
        """点击元素"""
        kwargs = {"selector": selector, "timeout": timeout, "waitForNav": wait_for_nav}
        if text:
            kwargs["text"] = text
        return await self.call_tool("chrome_click", **kwargs)

    async def fill(self, selector: str, value: str, method: str = "set", timeout: float = 5) -> dict:
        """填充表单"""
        return await self.call_tool("chrome_fill", selector=selector, value=value, method=method, timeout=timeout)

    async def extract(self, selector: str, attribute: str = "text", all: bool = False, timeout: float = 5) -> dict:
        """提取页面数据"""
        return await self.call_tool("chrome_extract_data", selector=selector, attribute=attribute, all=all, timeout=timeout)

    async def extract_window(self, path: str) -> dict:
        """读取 window 对象属性"""
        return await self.call_tool("chrome_extract_data", source="window", path=path)

    async def inject(self, code: str, world: str = "MAIN") -> dict:
        """在页面中执行 JavaScript"""
        return await self.call_tool("inject_script", code=code, world=world)

    async def keyboard(self, keys: str, selector: str = None, delay: int = 50) -> dict:
        """模拟键盘输入"""
        kwargs = {"keys": keys, "delay": delay}
        if selector:
            kwargs["selector"] = selector
        return await self.call_tool("chrome_keyboard", **kwargs)

    async def wait_for(self, selector: str, count: int = 1, timeout: float = 60) -> dict:
        """等待元素出现"""
        return await self.call_tool("chrome_wait_elements", selector=selector, count=count, timeout=int(timeout * 1000))

    async def scroll(self, direction: str = "down", amount: int = 300, selector: str = None) -> dict:
        """滚动页面"""
        kwargs = {"direction": direction, "amount": amount}
        if selector:
            kwargs["selector"] = selector
        return await self.call_tool("chrome_scroll", **kwargs)

    async def screenshot(self, format: str = "png") -> dict:
        """截取当前页面截图"""
        return await self.call_tool("chrome_screenshot", format=format)

    async def get_page_info(self) -> dict:
        """获取页面详细信息"""
        return await self.call_tool("chrome_get_page_info")

    async def read_page_data(self, path: str) -> dict:
        """读取页面数据 (window 属性)"""
        return await self.call_tool("read_page_data", path=path)

    async def tabs(self, action: str = "query_tabs", **params) -> dict:
        """标签页操作"""
        return await self.call_tool("browser_control", action=action, params=params)

    async def get_active_tab(self) -> dict:
        """获取当前活动标签页"""
        return await self.call_tool("browser_control", action="get_active_tab")

    async def close_tab(self, tab_id: int) -> dict:
        """关闭标签页"""
        return await self.call_tool("browser_control", action="close_tab", params={"tabId": tab_id})

    # ==================== 等待扩展连接 ====================

    async def wait_for_extension(self, timeout: float = 60):
        """等待扩展连接"""
        if self._extension_connected:
            return

        event = asyncio.Event()
        def on_connected(params):
            event.set()
        self.on_event("extension_connected", on_connected)

        # 也检查一下当前状态
        status = await self.get_status()
        if status.get("extensionConnected"):
            self._extension_connected = True
            self._extension_tools = status.get("tools", [])
            return

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception("等待扩展连接超时，请确保 Chrome 扩展已加载并点击图标连接")


# ==================== 演示 ====================

async def demo():
    """演示用法"""
    print("=" * 50)
    print("  Neurone 控制器 v2 演示")
    print("=" * 50)
    print()
    print("请确保:")
    print("  1. Relay 服务器已启动: python relay_server.py")
    print("  2. Chrome 扩展已加载并点击图标连接")
    print("  3. 已在扩展设置中授权网站权限")
    print()

    async with SilentAgentClient() as client:
        print("✓ 已连接到 Relay 服务器")

        # 等待扩展
        print("等待 Chrome 扩展...")
        await client.wait_for_extension(timeout=30)
        print(f"✓ 扩展已连接  工具: {client.tools}")
        print()

        # 导航
        print("导航到百度...")
        result = await client.navigate("https://www.baidu.com", new_tab=False)
        print(f"  结果: {result}")
        print()

        # 等待加载
        await asyncio.sleep(1)

        # 获取页面信息
        print("获取页面信息...")
        info = await client.get_page_info()
        print(f"  结果: {info}")
        print()

        # 提取标题
        print("提取标题...")
        title = await client.extract("title")
        print(f"  标题: {title}")
        print()

        # 填充搜索框
        print("填充搜索框...")
        await client.fill("#kw", "Neurone 浏览器自动化")
        print("  已填充")
        print()

        # 点击搜索按钮
        print("点击搜索...")
        await client.click("#su")
        print("  已点击")
        print()

        print("✓ 演示完成!")


if __name__ == "__main__":
    asyncio.run(demo())

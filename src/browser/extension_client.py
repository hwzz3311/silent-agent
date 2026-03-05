"""
扩展客户端

通过 Chrome 扩展控制浏览器（封装现有 relay_client）。
"""

from typing import Any, Dict, List, Optional
import asyncio

from src.ports.browser_port import BrowserPort
from src.core.result import Result
from ..relay_client import SilentAgentClient as RelayClient


class ExtensionClient(BrowserPort):
    """
    扩展客户端

    通过 Relay 服务器调用 Chrome 扩展工具。
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 18792,
        secret_key: str = None,
    ):
        self.host = host
        self.port = port
        self.secret_key = secret_key
        self._client: Optional[RelayClient] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    async def connect(self) -> None:
        """连接到 Relay 服务器"""
        self._client = RelayClient(
            host=self.host,
            port=self.port,
            secret_key=self.secret_key,
        )
        await self._client.connect()
        self._connected = True

    async def close(self) -> None:
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None
        self._connected = False

    async def _ensure_connected(self) -> None:
        """确保已连接"""
        if not self.is_connected:
            await self.connect()

    # ========== 页面操作 ==========

    async def navigate(self, url: str, new_tab: bool = True) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.navigate(url, new_tab=new_tab)
        return Result.ok(result)

    async def click(self, selector: str, text: str = None, timeout: float = 5) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.click(selector, text=text, timeout=timeout)
        return Result.ok(result)

    async def fill(self, selector: str, value: str, method: str = "set") -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.fill(selector, value, method=method)
        return Result.ok(result)

    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all: bool = False
    ) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.extract(selector, attribute=attribute, all=all)
        return Result.ok(result)

    async def evaluate(self, script: str, world: str = "MAIN") -> Result[dict]:
        """BrowserPort 接口：注入脚本执行"""
        await self._ensure_connected()
        result = await self._client.inject(code=script, world=world)
        return Result.ok(result)

    async def screenshot(self, format: str = "png") -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.screenshot(format=format)
        return Result.ok(result)

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None
    ) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.scroll(direction=direction, amount=amount, selector=selector)
        return Result.ok(result)

    async def wait_for(
        self,
        selector: str,
        count: int = 1,
        timeout: float = 60
    ) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.wait_for(selector, count=count, timeout=timeout)
        return Result.ok(result)

    async def keyboard(self, keys: str, selector: str = None) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.keyboard(keys, selector=selector)
        return Result.ok(result)

    # ========== 无障碍树 ==========

    async def get_a11y_tree(
        self,
        action: str = "get_tree",
        limit: int = 100,
        tab_id: int = None
    ) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.call_tool(
            "a11y_tree",
            action=action,
            limit=limit,
            tabId=tab_id,
        )
        return Result.ok(result)

    # ========== 标签页操作 ==========

    async def get_active_tab(self) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.get_active_tab()
        return Result.ok(result)

    async def close_tab(self, tab_id: int) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.close_tab(tab_id)
        return Result.ok(result)

    async def list_tabs(self) -> Result[dict]:
        await self._ensure_connected()
        result = await self._client.tab(action="query_tabs")
        return Result.ok(result.get("data", {}).get("tab", []))


__all__ = ["ExtensionClient"]

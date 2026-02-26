"""
扩展客户端

通过 Chrome 扩展控制浏览器（封装现有 relay_client）。
"""

from typing import Any, Dict, List, Optional
import asyncio

from .base import BrowserClient, BrowserClientError
from ..relay_client import SilentAgentClient as RelayClient


class ExtensionClient(BrowserClient):
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

    async def navigate(self, url: str, new_tab: bool = True) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.navigate(url, new_tab=new_tab)

    async def click(self, selector: str, text: str = None, timeout: float = 5) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.click(selector, text=text, timeout=timeout)

    async def fill(self, selector: str, value: str, method: str = "set") -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.fill(selector, value, method=method)

    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all: bool = False
    ) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.extract(selector, attribute=attribute, all=all)

    async def inject(self, code: str, world: str = "MAIN") -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.inject(code, world=world)

    async def screenshot(self, format: str = "png") -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.screenshot(format=format)

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None
    ) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.scroll(direction=direction, amount=amount, selector=selector)

    async def wait_for(
        self,
        selector: str,
        count: int = 1,
        timeout: float = 60
    ) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.wait_for(selector, count=count, timeout=timeout)

    async def keyboard(self, keys: str, selector: str = None) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.keyboard(keys, selector=selector)

    # ========== 无障碍树 ==========

    async def get_a11y_tree(
        self,
        action: str = "get_tree",
        limit: int = 100,
        tab_id: int = None
    ) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.call_tool(
            "a11y_tree",
            action=action,
            limit=limit,
            tabId=tab_id,
        )

    # ========== 标签页操作 ==========

    async def get_active_tab(self) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.get_active_tab()

    async def close_tab(self, tab_id: int) -> Dict[str, Any]:
        await self._ensure_connected()
        return await self._client.close_tab(tab_id)

    async def list_tabs(self) -> List[Dict[str, Any]]:
        await self._ensure_connected()
        result = await self._client.tab(action="query_tabs")
        return result.get("data", {}).get("tabs", [])


__all__ = ["ExtensionClient"]
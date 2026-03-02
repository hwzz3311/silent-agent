"""
混合模式客户端

协调 Puppeteer 和扩展客户端，提供最佳的无障碍树获取能力。
"""

from typing import Any, Dict, List, Optional

from .base import BrowserClient, BrowserClientError
from .puppeteer_client import PuppeteerClient
from .extension_client import ExtensionClient


class HybridClient(BrowserClient):
    """
    混合模式客户端

    结合 Puppeteer 和扩展客户端的优势：
    - Puppeteer: 提供真实无障碍树、高隐蔽性
    - 扩展: 提供复杂的页面交互能力

    无障碍树由 Puppeteer 获取，其他操作可灵活选择。
    """

    def __init__(
        self,
        puppeteer_config: dict = None,
        extension_config: dict = None,
    ):
        self.puppeteer_config = puppeteer_config or {}
        self.extension_config = extension_config or {}
        self._puppeteer: Optional[PuppeteerClient] = None
        self._extension: Optional[ExtensionClient] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """启动两个客户端"""
        # 启动 Puppeteer
        self._puppeteer = PuppeteerClient(
            headless=self.puppeteer_config.get("headless", True),
            args=self.puppeteer_config.get("args", []),
            stealth=self.puppeteer_config.get("stealth", True),
            executable_path=self.puppeteer_config.get("executable_path"),
            browser_ws_endpoint=self.puppeteer_config.get("browser_ws_endpoint"),
        )
        await self._puppeteer.connect()

        # 启动扩展客户端
        self._extension = ExtensionClient(
            host=self.extension_config.get("host", "127.0.0.1"),
            port=self.extension_config.get("port", 18792),
            secret_key=self.extension_config.get("secret_key"),
        )
        try:
            await self._extension.connect()
        except Exception as e:
            # 扩展连接失败不影响混合模式（可以只用 Puppeteer）
            print(f"[HybridClient] 扩展连接失败: {e}")
            self._extension = None

        self._connected = True

    async def close(self) -> None:
        """关闭两个客户端"""
        if self._puppeteer:
            await self._puppeteer.close()
            self._puppeteer = None

        if self._extension:
            await self._extension.close()
            self._extension = None

        self._connected = False

    async def _ensure_connected(self) -> None:
        if not self.is_connected:
            await self.connect()

    # ========== 页面操作（优先使用扩展） ==========

    async def navigate(self, url: str, new_tab: bool = True) -> Dict[str, Any]:
        """导航：优先使用 Puppeteer（更可靠）"""
        await self._ensure_connected()
        return await self._puppeteer.navigate(url, new_tab=new_tab)

    async def click(self, selector: str, text: str = None, timeout: float = 5) -> Dict[str, Any]:
        """点击：优先使用扩展（Puppeteer 点击有时不触发事件）"""
        await self._ensure_connected()
        if self._extension:
            return await self._extension.click(selector, text=text, timeout=timeout)
        return await self._puppeteer.click(selector, text=text, timeout=timeout)

    async def fill(self, selector: str, value: str, method: str = "set") -> Dict[str, Any]:
        """填充：优先使用扩展"""
        await self._ensure_connected()
        if self._extension:
            return await self._extension.fill(selector, value, method=method)
        return await self._puppeteer.fill(selector, value, method=method)

    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all: bool = False
    ) -> Dict[str, Any]:
        """提取：优先使用扩展"""
        await self._ensure_connected()
        if self._extension:
            return await self._extension.extract(selector, attribute=attribute, all=all)
        return await self._puppeteer.extract(selector, attribute=attribute, all=all)

    async def inject(self, code: str, world: str = "MAIN") -> Dict[str, Any]:
        """注入脚本：两者都可以"""
        await self._ensure_connected()
        if self._extension:
            return await self._extension.inject(code, world=world)
        return await self._puppeteer.inject(code, world=world)

    async def screenshot(self, format: str = "png") -> Dict[str, Any]:
        """截图：优先使用 Puppeteer（更稳定）"""
        await self._ensure_connected()
        return await self._puppeteer.screenshot(format=format)

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None
    ) -> Dict[str, Any]:
        """滚动：优先使用扩展"""
        await self._ensure_connected()
        if self._extension:
            return await self._extension.scroll(direction=direction, amount=amount, selector=selector)
        return await self._puppeteer.scroll(direction=direction, amount=amount, selector=selector)

    async def wait_for(
        self,
        selector: str,
        count: int = 1,
        timeout: float = 60
    ) -> Dict[str, Any]:
        """等待：两者都可以"""
        await self._ensure_connected()
        if self._extension:
            return await self._extension.wait_for(selector, count=count, timeout=timeout)
        return await self._puppeteer.wait_for(selector, count=count, timeout=timeout)

    async def keyboard(self, keys: str, selector: str = None) -> Dict[str, Any]:
        """键盘：优先使用扩展"""
        await self._ensure_connected()
        if self._extension:
            return await self._extension.keyboard(keys, selector=selector)
        return await self._puppeteer.keyboard(keys, selector=selector)

    # ========== 无障碍树（核心优势：真实树） ==========

    async def get_a11y_tree(
        self,
        action: str = "get_tree",
        limit: int = 100,
        tab_id: int = None
    ) -> Dict[str, Any]:
        """
        获取无障碍树：使用 Puppeteer 获取真实树

        这是混合模式的核心优势：通过 Puppeteer CDP 获取真实无障碍树。
        """
        await self._ensure_connected()

        if self._puppeteer:
            # 优先使用 Puppeteer 获取真实无障碍树
            result = await self._puppeteer.get_a11y_tree(action=action, limit=limit)

            if result.get("success"):
                return result

            # 如果 Puppeteer 失败，尝试 CDP
            if action == "get_tree":
                cdp_result = await self._puppeteer.get_a11y_tree_via_cdp(limit=limit)
                if cdp_result.get("success"):
                    return cdp_result

        # 回退到扩展
        if self._extension:
            return await self._extension.get_a11y_tree(action=action, limit=limit, tab_id=tab_id)

        return {"success": False, "error": "无可用的无障碍树获取方式"}

    # ========== 标签页操作 ==========

    async def get_active_tab(self) -> Dict[str, Any]:
        await self._ensure_connected()
        if self._puppeteer:
            return await self._puppeteer.get_active_tab()
        if self._extension:
            return await self._extension.get_active_tab()
        return {"success": False, "error": "未连接"}

    async def close_tab(self, tab_id: int) -> Dict[str, Any]:
        await self._ensure_connected()
        if self._extension:
            return await self._extension.close_tab(tab_id)
        return {"success": False, "error": "Puppeteer 不支持按 ID 关闭"}

    async def list_tabs(self) -> List[Dict[str, Any]]:
        await self._ensure_connected()
        if self._puppeteer:
            return await self._puppeteer.list_tabs()
        if self._extension:
            return await self._extension.list_tabs()
        return []


__all__ = ["HybridClient"]
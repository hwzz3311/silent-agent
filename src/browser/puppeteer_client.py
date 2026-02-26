"""
Puppeteer 客户端

通过 Puppeteer 控制浏览器，支持 stealth 模式。
"""

import asyncio
import base64
import json
from typing import Any, Dict, List, Optional

from .base import BrowserClient, BrowserClientError

# Puppeteer 相关导入
# 注意：需要安装 puppeteer-extra 和 puppeteer-extra-plugin-stealth
try:
    import puppeteer
    from puppeteer import launch as puppeteer_launch
    PUPPETEER_AVAILABLE = True
except ImportError:
    PUPPETEER_AVAILABLE = False
    puppeteer = None
    puppeteer_launch = None

try:
    from puppeteer_extra import launch as puppeteer_extra_launch
    from puppeteer_extra_plugin_stealth import stealth
    STEALTH_PLUGIN_AVAILABLE = True
except ImportError:
    STEALTH_PLUGIN_AVAILABLE = False
    puppeteer_extra_launch = None
    stealth = None


class PuppeteerClient(BrowserClient):
    """
    Puppeteer 客户端

    通过 Puppeteer 控制浏览器，支持 stealth 模式。
    """

    def __init__(
        self,
        headless: bool = True,
        args: list = None,
        stealth: bool = True,
        user_data_dir: str = None,
    ):
        self.headless = headless
        self.args = args or []
        self.stealth_enabled = stealth
        self.user_data_dir = user_data_dir
        self._browser = None
        self._page = None
        self._cdp_session = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._browser is not None

    async def connect(self) -> None:
        """启动浏览器"""
        if not PUPPETEER_AVAILABLE:
            raise BrowserClientError(
                "Puppeteer 未安装，请运行: pip install puppeteer-extra puppeteer-extra-plugin-stealth"
            )

        # 构建启动参数
        launch_args = {
            "headless": self.headless,
            "args": self.args.copy() if self.args else [],
            "ignoreDefaultArgs": ["--enable-automation"],  # 隐藏自动化特征
        }

        # 添加 stealth 插件
        if self.stealth_enabled and STEALTH_PLUGIN_AVAILABLE:
            try:
                # 使用 puppeteer-extra 加载 stealth 插件
                self._browser = await puppeteer_extra_launch(
                    **launch_args,
                    plugins=[stealth()],
                )
            except Exception as e:
                # 如果 stealth 插件失败，回退到普通模式
                print(f"[PuppeteerClient] Stealth 插件加载失败，回退到普通模式: {e}")
                self._browser = await puppeteer_launch(**launch_args)
        else:
            self._browser = await puppeteer_launch(**launch_args)

        # 创建页面
        pages = await self._browser.pagesArray()
        if pages:
            self._page = pages[0]
        else:
            self._page = await self._browser.newPage()

        self._connected = True

    async def close(self) -> None:
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        self._page = None
        self._cdp_session = None
        self._connected = False

    async def _ensure_connected(self) -> None:
        """确保已连接"""
        if not self.is_connected:
            await self.connect()

    async def _get_cdp_session(self):
        """获取 CDP 会话"""
        if self._cdp_session is None and self._page:
            self._cdp_session = await self._page.target.createCDPSession()
        return self._cdp_session

    # ========== 页面操作 ==========

    async def navigate(self, url: str, new_tab: bool = True) -> Dict[str, Any]:
        await self._ensure_connected()

        if new_tab:
            self._page = await self._browser.newPage()

        try:
            await self._page.goto(url, {"waitUntil": "networkidle0", "timeout": 30000})
            return {"success": True, "url": url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def click(self, selector: str, text: str = None, timeout: float = 5) -> Dict[str, Any]:
        await self._ensure_connected()

        try:
            # 如果指定了 text，先查找匹配元素
            if text:
                elements = await self._page.querySelectorAll(selector)
                for el in elements:
                    el_text = await self._page.evaluate("(el) => el.textContent", el)
                    if text in el_text:
                        await el.click()
                        return {"success": True, "selector": selector}
                return {"success": False, "error": f"未找到包含文本 '{text}' 的元素"}

            # 直接点击
            await self._page.click(selector, {"timeout": timeout * 1000})
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def fill(self, selector: str, value: str, method: str = "set") -> Dict[str, Any]:
        await self._ensure_connected()

        try:
            if method == "set":
                # 使用 Puppeteer 的类型功能，更自然
                await self._page.type(selector, value)
            else:
                # 直接设置值
                await self._page.evaluate(
                    f"""(selector, value) => {{
                        const el = document.querySelector(selector);
                        if (el) {{ el.value = value; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }}
                    }}""",
                    selector, value,
                )
            return {"success": True, "selector": selector, "value": value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all: bool = False
    ) -> Dict[str, Any]:
        await self._ensure_connected()

        try:
            if all:
                elements = await self._page.querySelectorAll(selector)
                results = []
                for el in elements:
                    if attribute == "text":
                        text = await self._page.evaluate("(el) => el.textContent", el)
                        results.append(text.strip())
                    elif attribute == "html":
                        html = await self._page.evaluate("(el) => el.outerHTML", el)
                        results.append(html)
                    else:
                        results.append(await el.getProperty(attribute))
                return {"success": True, "data": results}
            else:
                el = await self._page.querySelector(selector)
                if not el:
                    return {"success": False, "error": "元素未找到"}

                if attribute == "text":
                    text = await self._page.evaluate("(el) => el.textContent", el)
                    return {"success": True, "data": text.strip()}
                elif attribute == "html":
                    html = await self._page.evaluate("(el) => el.outerHTML", el)
                    return {"success": True, "data": html}
                else:
                    prop = await el.getProperty(attribute)
                    return {"success": True, "data": prop}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def inject(self, code: str, world: str = "MAIN") -> Dict[str, Any]:
        await self._ensure_connected()

        try:
            result = await self._page.evaluate(code)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def screenshot(self, format: str = "png") -> Dict[str, Any]:
        await self._ensure_connected()

        try:
            options = {"type": format} if format == "png" else {"type": "jpeg", "quality": 80}
            screenshot_data = await self._page.screenshot(options)

            # 转换为 base64
            if isinstance(screenshot_data, bytes):
                b64 = base64.b64encode(screenshot_data).decode()
            else:
                b64 = screenshot_data

            return {"success": True, "data": b64, "format": format}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None
    ) -> Dict[str, Any]:
        await self._ensure_connected()

        try:
            if selector:
                # 滚动到指定元素
                await self._page.evaluate(
                    f"""(selector) => {{
                        const el = document.querySelector(selector);
                        if (el) el.scrollIntoView();
                    }}""",
                    selector,
                )
            else:
                # 滚动页面
                await self._page.evaluate(
                    f"""(direction, amount) => {{
                        const scroll = direction === 'up' ? -amount : amount;
                        window.scrollBy(0, scroll);
                    }}""",
                    direction, amount,
                )
            return {"success": True, "direction": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def wait_for(
        self,
        selector: str,
        count: int = 1,
        timeout: float = 60
    ) -> Dict[str, Any]:
        await self._ensure_connected()

        try:
            await self._page.waitForSelector(
                selector,
                {"visible": True, "timeout": timeout * 1000}
            )
            # 检查数量
            elements = await self._page.querySelectorAll(selector)
            actual_count = len(elements)

            if actual_count >= count:
                return {"success": True, "count": actual_count}
            else:
                return {"success": False, "error": f"元素数量不足: 期望 {count}, 实际 {actual_count}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def keyboard(self, keys: str, selector: str = None) -> Dict[str, Any]:
        await self._ensure_connected()

        try:
            # 聚焦到指定元素
            if selector:
                await self._page.focus(selector)

            # 逐个按键输入
            await self._page.keyboard.type(keys)
            return {"success": True, "keys": keys}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ========== 无障碍树 ==========

    async def get_a11y_tree(
        self,
        action: str = "get_tree",
        limit: int = 100,
        tab_id: int = None
    ) -> Dict[str, Any]:
        """
        获取无障碍树

        使用 Puppeteer 的 accessibility.snapshot() 获取真实无障碍树。
        """
        await self._ensure_connected()

        try:
            if action == "get_tree":
                # 方法1: 使用 Puppeteer 内置的 accessibility API
                snapshot = await self._page.accessibility.snapshot()

                # 简化结构以匹配现有格式
                nodes = {}
                root_ids = []

                def process_node(node, parent_id=None):
                    node_id = str(node.get("nodeId", id(nodes)))
                    role = node.get("role", "unknown")
                    name = node.get("name", "")
                    value = node.get("value", "")

                    nodes[node_id] = {
                        "id": node_id,
                        "role": role,
                        "name": name,
                        "value": value,
                        "children": [],
                    }

                    if parent_id:
                        nodes[parent_id]["children"].append(node_id)
                    else:
                        root_ids.append(node_id)

                    # 递归处理子节点
                    children = node.get("children", [])
                    for child in children[:limit]:  # 限制数量
                        process_node(child, node_id)

                if snapshot:
                    process_node(snapshot)

                return {
                    "success": True,
                    "data": {
                        "rootIds": root_ids[:limit],
                        "nodes": dict(list(nodes.items())[:limit]),
                        "totalNode": len(nodes),
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                }

            elif action == "get_focused":
                # 获取焦点元素
                focused = await self._page.accessibility.getAXNode()
                return {"success": True, "data": focused}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_a11y_tree_via_cdp(self, limit: int = 100) -> Dict[str, Any]:
        """
        通过 CDP 获取完整的无障碍树

        这将获取比 Puppeteer accessibility.snapshot() 更详细的树。
        """
        await self._ensure_connected()

        try:
            cdp = await self._get_cdp_session()

            # 启用 Accessibility 域
            await cdp.send("Accessibility.enable")

            # 获取完整树
            result = await cdp.send("Accessibility.getFullAXTree")

            await cdp.send("Accessibility.disable")

            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ========== 标签页操作 ==========

    async def get_active_tab(self) -> Dict[str, Any]:
        await self._ensure_connected()
        return {"success": True, "data": {"url": self._page.url}}

    async def close_tab(self, tab_id: int) -> Dict[str, Any]:
        await self._ensure_connected()
        # 注意：Puppeteer 中 tab_id 概念不同
        return {"success": False, "error": "Puppeteer 不支持按 ID 关闭标签页"}

    async def list_tabs(self) -> List[Dict[str, Any]]:
        await self._ensure_connected()
        pages = await self._browser.pageArray()
        return [
            {"url": p.url, "title": p.title}
            for p in pages if p.url
        ]


__all__ = ["PuppeteerClient"]
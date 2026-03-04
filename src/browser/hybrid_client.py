"""
混合模式客户端

协调 Puppeteer 和扩展客户端，提供最佳的无障碍树获取能力。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .base import BrowserClient, BrowserClientError
from .puppeteer_client import PuppeteerClient
from .extension_client import ExtensionClient

logger = logging.getLogger(__name__)


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

    async def connect(self, timeout: float = 10) -> None:
        """启动两个客户端（带超时）"""
        logger.info("[HybridClient] 开始连接...")
        logger.info(f"[HybridClient] puppeteer_config: {self.puppeteer_config}")

        # 启动 Puppeteer
        browser_ws_endpoint = self.puppeteer_config.get("browser_ws_endpoint")
        logger.info(f"[HybridClient] browser_ws_endpoint: {browser_ws_endpoint}")
        self._puppeteer = PuppeteerClient(
            headless=self.puppeteer_config.get("headless", True),
            args=self.puppeteer_config.get("args", []),
            stealth=self.puppeteer_config.get("stealth", True),
            executable_path=self.puppeteer_config.get("executable_path"),
            browser_ws_endpoint=browser_ws_endpoint,
        )
        try:
            await asyncio.wait_for(self._puppeteer.connect(), timeout=timeout)
            logger.info("[HybridClient] Puppeteer 连接成功")
        except asyncio.TimeoutError:
            logger.warning(f"[HybridClient] Puppeteer 连接超时 ({timeout}秒)，跳过")
            self._puppeteer = None
        except Exception as e:
            logger.warning(f"[HybridClient] Puppeteer 连接失败: {e}，跳过")
            self._puppeteer = None

        # 启动扩展客户端
        self._extension = ExtensionClient(
            host=self.extension_config.get("host", "127.0.0.1"),
            port=self.extension_config.get("port", 18792),
            secret_key=self.extension_config.get("secret_key"),
        )
        try:
            await asyncio.wait_for(self._extension.connect(), timeout=timeout)
            logger.info("[HybridClient] 扩展连接成功")
        except asyncio.TimeoutError:
            logger.warning(f"[HybridClient] 扩展连接超时 ({timeout}秒)，跳过")
            self._extension = None
        except Exception as e:
            # 扩展连接失败不影响混合模式（可以只用 Puppeteer）
            logger.warning(f"[HybridClient] 扩展连接失败: {e}，跳过")
            self._extension = None

        self._connected = True
        logger.info(f"[HybridClient] 连接完成，Puppeteer: {self._puppeteer is not None}, 扩展: {self._extension is not None}")

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
        """导航：优先使用 Puppeteer（更可靠），不可用时使用 Extension"""
        await self._ensure_connected()
        if self._puppeteer:
            return await self._puppeteer.navigate(url, new_tab=new_tab)
        elif self._extension:
            return await self._extension.navigate(url, new_tab=new_tab)
        return {"success": False, "error": "无可用的浏览器客户端"}

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

    # ========== 工具执行接口（T2.5.3） ==========

    async def execute_tool(
        self,
        name: str,
        params: Dict[str, Any] = None,
        timeout: float = 60,
        context: Any = None,
        secret_key: str = None,
    ) -> Dict[str, Any]:
        """
        执行工具（统一接口）

        将工具名称映射到具体方法：
        - browser.navigate -> navigate
        - browser.click -> click
        - browser.fill -> fill
        - browser.extract -> extract
        - browser.screenshot -> screenshot
        - browser.wait -> wait_for
        - browser.keyboard -> keyboard
        - browser.inject -> inject
        - a11y_tree -> get_a11y_tree
        - chrome_navigate -> navigate
        - chrome_click -> click
        - chrome_fill -> fill
        - read_page_data -> extract
        - browser_control -> _puppeteer 控制方法
        - inject_script -> inject
        """
        from typing import Dict, Any

        await self._ensure_connected()
        params = params or {}

        # 映射表
        tool_mapping = {
            # 统一命名
            "browser.navigate": "navigate",
            "browser.click": "click",
            "browser.fill": "fill",
            "browser.extract": "extract",
            "browser.screenshot": "screenshot",
            "browser.wait": "wait_for",
            "browser.keyboard": "keyboard",
            "browser.inject": "inject",
            # 无障碍树
            "a11y_tree": "get_a11y_tree",
            # 兼容旧命名
            "chrome_navigate": "navigate",
            "chrome_click": "click",
            "chrome_fill": "fill",
            "read_page_data": "extract",
            "inject_script": "inject",
        }

        # 浏览器控制操作
        if name == "browser_control":
            action = params.get("action", "")
            # 优先使用 Puppeteer，如果不可用则使用 Extension
            if action == "get_active_tab":
                if self._puppeteer:
                    return await self._puppeteer.get_active_tab()
                elif self._extension:
                    return await self._extension.get_active_tab()
                return {"success": False, "error": "无可用的浏览器客户端"}
            elif action == "list_tabs":
                if self._puppeteer:
                    return await self._puppeteer.list_tabs()
                elif self._extension:
                    tabs = await self._extension.list_tabs()
                    return {"success": True, "data": tabs}
                return {"success": False, "error": "无可用的浏览器客户端"}
            elif action == "close_tab":
                tab_id = params.get("tab_id")
                if self._extension:
                    return await self._extension.close_tab(tab_id)
                return {"success": False, "error": "Puppeteer 不支持按 ID 关闭标签页"}
            elif action == "new_tab":
                url = params.get("url", "about:blank")
                return await self.navigate(url, new_tab=True)
            return {"success": False, "error": f"未知 action: {action}"}

        # 查找映射方法
        method_name = tool_mapping.get(name)

        if not method_name:
            # 检查是否是业务工具（Python 端直接执行）
            from src.client.client import BUSINESS_TOOLS
            if name in BUSINESS_TOOLS:
                # 将 self 注入到 context 中，方便业务工具访问浏览器
                if context is None:
                    from src.tools.base import ExecutionContext
                    context = ExecutionContext()
                context.client = self

                # 调用业务工具
                try:
                    result = await self._execute_business_tool(name, params, context)
                    return result
                except Exception as e:
                    return {"success": False, "error": f"业务工具执行失败: {e}"}

            return {"success": False, "error": f"未知工具: {name}"}

        # 获取方法
        method = getattr(self, method_name, None)
        if not method:
            return {"success": False, "error": f"方法不存在: {method_name}"}

        # 提取参数并调用
        try:
            # 根据方法签名提取参数
            import inspect

            sig = inspect.signature(method)
            call_params = {}

            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                if param_name in params:
                    call_params[param_name] = params[param_name]
                elif param.default == inspect.Parameter.empty:
                    # 必填参数尝试从 params 获取
                    pass

            result = await method(**call_params)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ========== 业务工具执行 ==========

    async def _execute_business_tool(
        self,
        name: str,
        params: Dict[str, Any] = None,
        context: Any = None
    ) -> Dict[str, Any]:
        """
        直接执行 Python 业务工具（不经过 relay_server）

        Args:
            name: 工具名称
            params: 工具参数
            context: 执行上下文（包含 client 等资源）

        Returns:
            工具执行结果
        """
        from src.client.client import BUSINESS_TOOLS
        import importlib
        import inspect

        if name not in BUSINESS_TOOLS:
            raise ValueError(f"未知业务工具: {name}")

        module_path, func_name = BUSINESS_TOOLS[name]

        # 动态导入模块和函数
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        # 调用函数
        try:
            import asyncio
            sig = inspect.signature(func)
            if 'context' in sig.parameters:
                # 函数支持 context 参数
                result = func(**(params or {}), context=context)
            elif hasattr(func, 'execute') or hasattr(func, '_execute_core'):
                # 这是一个 Tool 类实例或类方法
                tool_func = getattr(module, func_name, None)
                if tool_func and callable(tool_func):
                    result = tool_func(**(params or {}))
                else:
                    result = func(**(params or {}))
            else:
                result = func(**(params or {}))

            # 如果结果是 coroutine，需要 await
            if asyncio.iscoroutine(result):
                result = await result

            # 自动转换 Result 对象为标准格式
            return self._convert_result(result)
        except Exception as e:
            raise ConnectionError(f"业务工具执行失败: {e}")

    def _convert_result(self, result: Any) -> Dict[str, Any]:
        """将 Result 对象转换为标准 API 格式"""
        from src.core.result import Result
        from pydantic import BaseModel

        # 如果不是 Result 对象检查是否是 Pydantic 模型
        if not isinstance(result, Result):
            if isinstance(result, BaseModel):
                # Pydantic 模型转换为字典
                return {
                    "success": result.success,
                    "data": result.model_dump(),
                    "error": None
                }
            return result

        # 转换 Result 对象
        return {
            "success": result.success,
            "data": result.data,
            "error": str(result.error) if result.error else None
        }

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
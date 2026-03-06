"""
混合模式客户端

协调 Puppeteer 和扩展客户端，提供最佳的无障碍树获取能力。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.ports.browser_port import BrowserPort
from src.core.result import Result
from .puppeteer import PuppeteerClient
from .extension import ExtensionClient
from .router import DefaultRoutingStrategy

from src.tools.domain.registry import BusinessToolRegistry, get_registry
from src.core.result import Result, ResultMeta, Error

logger = logging.getLogger(__name__)



class HybridClient(BrowserPort):
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
        self._strategy = DefaultRoutingStrategy()

    def _select_client(self, operation: str):
        """根据操作类型选择客户端"""
        return self._strategy.select_client(
            operation, self._puppeteer, self._extension
        )

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

    async def navigate(self, url: str, **kwargs) -> Result[dict]:
        """导航：使用 Puppeteer"""
        await self._ensure_connected()
        new_tab = kwargs.get("new_tab", True)
        client = self._select_client("navigate")
        if client:
            result = await client.navigate(url, new_tab=new_tab)
            return Result.ok(result)
        return Result.ok({"success": False, "error": "无可用的浏览器客户端"})

    async def click(self, selector: str, **kwargs) -> Result[dict]:
        """点击：优先使用扩展"""
        await self._ensure_connected()
        client = self._select_client("click")
        text = kwargs.get("text")
        timeout = kwargs.get("timeout", 5)
        result = await client.click(selector, text=text, timeout=timeout)
        return Result.ok(result)

    async def fill(self, selector: str, value: str, **kwargs) -> Result[dict]:
        """填充：优先使用扩展"""
        await self._ensure_connected()
        client = self._select_client("fill")
        method = kwargs.get("method", "set")
        result = await client.fill(selector, value, method=method)
        return Result.ok(result)

    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all: bool = False,
        **kwargs
    ) -> Result[dict]:
        """提取：优先使用扩展"""
        await self._ensure_connected()
        client = self._select_client("extract")
        result = await client.extract(selector, attribute=attribute, all=all)
        return Result.ok(result)

    async def evaluate(self, script: str, **kwargs) -> Result[dict]:
        """注入脚本：灵活选择"""
        await self._ensure_connected()
        client = self._select_client("evaluate")
        world = kwargs.get("world", "MAIN")
        result = await client.inject(script, world=world)
        return Result.ok(result)

    async def screenshot(self, **kwargs) -> Result[dict]:
        """截图：使用 Puppeteer"""
        await self._ensure_connected()
        client = self._select_client("screenshot")
        format = kwargs.get("format", "png")
        result = await client.screenshot(format=format)
        return Result.ok(result)

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None,
        **kwargs
    ) -> Result[dict]:
        """滚动：优先使用扩展"""
        await self._ensure_connected()
        client = self._select_client("scroll")
        result = await client.scroll(direction=direction, amount=amount, selector=selector)
        return Result.ok(result)

    async def wait_for(
        self,
        selector: str,
        timeout: int = 30000,
        **kwargs
    ) -> Result[dict]:
        """等待：灵活选择"""
        await self._ensure_connected()
        client = self._select_client("wait_for")
        count = kwargs.get("count", 1)
        result = await client.wait_for(selector, count=count, timeout=timeout)
        return Result.ok(result)

    async def keyboard(self, keys: str, selector: str = None, **kwargs) -> Result[dict]:
        """键盘：优先使用扩展"""
        await self._ensure_connected()
        client = self._select_client("keyboard")
        result = await client.keyboard(keys, selector=selector)
        return Result.ok(result)

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
            from src.tools.domain.registry import get_registry
            registry = get_registry()
            if registry.is_registered(name):
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

        使用 BusinessToolRegistry 作为单一真相来源。

        Args:
            name: 工具名称
            params: 工具参数
            context: 执行上下文（包含 client 等资源）

        Returns:
            工具执行结果
        """
        from src.tools.domain.registry import get_registry
        registry = get_registry()

        # 检查工具是否已注册
        if not registry.is_registered(name):
            available = registry.list_all()
            raise ValueError(f"未知业务工具: {name}，可用工具: {available[:5]}...")

        # 确保 context 有 client 属性
        if context is None:
            from src.tools.base import ExecutionContext
            context = ExecutionContext()
        context.client = self

        # 从 Registry 获取工具并创建新实例
        tool_instance = registry.create_instance(name)
        if tool_instance is None:
            raise ValueError(f"无法创建工具实例: {name}")

        # 参数验证已移至 BusinessTool.execute()，此处只做 pydantic 转换
        params = params or {}

        # 获取参数类型并验证转换
        params_type = tool_instance._get_params_type()
        if isinstance(params_type, type) and hasattr(params_type, 'model_validate'):
            validated_params = params_type.model_validate(params)
        elif isinstance(params_type, type) and hasattr(params_type, 'parse_obj'):
            validated_params = params_type.parse_obj(params)
        else:
            validated_params = params

        # 直接执行工具（异步 await）
        result = await tool_instance.execute(validated_params, context)

        # 转换 Result 为 Dict
        return self._convert_result(result)

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

    async def get_a11y_tree(self, **kwargs) -> Result[dict]:
        """
        获取无障碍树：使用 Puppeteer 获取真实树

        这是混合模式的核心优势：通过 Puppeteer CDP 获取真实无障碍树。
        """
        await self._ensure_connected()

        action = kwargs.get("action", "get_tree")
        limit = kwargs.get("limit", 100)
        tab_id = kwargs.get("tab_id")

        client = self._select_client("get_a11y_tree")

        if client == self._puppeteer and self._puppeteer:
            # 优先使用 Puppeteer 获取真实无障碍树
            result = await self._puppeteer.get_a11y_tree(action=action, limit=limit)

            if result.get("success"):
                return Result.ok(result)

            # 如果 Puppeteer 失败，尝试 CDP
            if action == "get_tree":
                cdp_result = await self._puppeteer.get_a11y_tree_via_cdp(limit=limit)
                if cdp_result.get("success"):
                    return Result.ok(cdp_result)

        # 回退到扩展
        if self._extension:
            result = await self._extension.get_a11y_tree(action=action, limit=limit, tab_id=tab_id)
            return Result.ok(result)

        return Result.ok({"success": False, "error": "无可用的无障碍树获取方式"})

    # ========== 标签页操作 ==========

    async def get_active_tab(self) -> Result[dict]:
        await self._ensure_connected()
        client = self._select_client("get_active_tab")
        if client:
            result = await client.get_active_tab()
            return Result.ok(result)
        return Result.ok({"success": False, "error": "未连接"})

    async def close_tab(self, tab_id: int) -> Result[dict]:
        await self._ensure_connected()
        if self._extension:
            result = await self._extension.close_tab(tab_id)
            return Result.ok(result)
        return Result.ok({"success": False, "error": "Puppeteer 不支持按 ID 关闭"})

    async def list_tabs(self) -> Result[list]:
        await self._ensure_connected()
        client = self._select_client("list_tabs")
        if client:
            result = await client.list_tabs()
            return Result.ok(result)
        return Result.ok([])


__all__ = ["HybridClient"]
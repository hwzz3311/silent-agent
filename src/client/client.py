"""
WebSocket 客户端模块

提供 SilentAgentClient 客户端类。
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

from .connection import ConnectionManager, ConnectionConfig, ConnectionInfo
from .exceptions import (
    ConnectionError,
    DisconnectedError,
    TimeoutError,
)


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 业务工具映射：API 工具名 -> (Python 模块路径, 函数名)
# 这些工具在 Python 端实现，直接调用不经过 extension
BUSINESS_TOOLS = {
    # 登录相关
    "xhs_check_login_status": (
        "src.tools.sites.xiaohongshu.tools.login",
        "check_login_status",
    ),
    "xhs_get_login_qrcode": (
        "src.tools.sites.xiaohongshu.tools.login",
        "get_login_qrcode",
    ),
    "xhs_wait_login": (
        "src.tools.sites.xiaohongshu.tools.login",
        "wait_login",
    ),
    "xhs_delete_cookies": (
        "src.tools.sites.xiaohongshu.tools.login",
        "delete_cookies",
    ),
    # 浏览相关
    "xhs_list_feeds": (
        "src.tools.sites.xiaohongshu.tools.browse",
        "list_feeds",
    ),
    "xhs_search_feeds": (
        "src.tools.sites.xiaohongshu.tools.browse",
        "search_feeds",
    ),
    "xhs_get_feed_detail": (
        "src.tools.sites.xiaohongshu.tools.browse",
        "get_feed_detail",
    ),
    "xhs_user_profile": (
        "src.tools.sites.xiaohongshu.tools.browse",
        "user_profile",
    ),
    # 互动相关
    "xhs_like_feed": (
        "src.tools.sites.xiaohongshu.tools.interact",
        "like_feed",
    ),
    "xhs_favorite_feed": (
        "src.tools.sites.xiaohongshu.tools.interact",
        "favorite_feed",
    ),
    "xhs_post_comment": (
        "src.tools.sites.xiaohongshu.tools.interact",
        "post_comment",
    ),
    "xhs_reply_comment": (
        "src.tools.sites.xiaohongshu.tools.interact",
        "reply_comment",
    ),
    # 发布相关
    "xhs_publish": (
        "src.tools.sites.xiaohongshu.publishers",
        "publish_note",
    ),
    "xhs_publish_content": (
        "src.tools.sites.xiaohongshu.publishers",
        "publish_note",
    ),
    "xhs_publish_video": (
        "src.tools.sites.xiaohongshu.publishers",
        "publish_video",
    ),
}


class SilentAgentClient:
    """
    Neurone WebSocket 客户端

    通过 Relay 服务器远程调用浏览器扩展中的工具。

    用法:
        async with SilentAgentClient() as client:
            await client.connect()
            result = await client.execute_tool("browser.click", {"selector": "#btn"})
    """

    # API 工具名 -> 扩展工具名 映射
    TOOL_NAME_MAP = {
        "browser.click": "chrome_click",
        "browser.navigate": "chrome_navigate",
        "browser.fill": "chrome_fill",
        "browser.extract": "chrome_extract_data",
        "browser.keyboard": "chrome_keyboard",
        "browser.scroll": "chrome_scroll",
        "browser.screenshot": "chrome_screenshot",
        "browser.wait_elements": "chrome_wait_elements",
        "browser.get_page_info": "chrome_get_page_info",
        "inject_script": "inject_script",
        "a11y_tree": "a11y_tree",
    }

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 18792,
        path: str = "/controller",
        auto_reconnect: bool = True,
        reconnect_delay: float = 5.0,
        secret_key: str = None,
    ):
        self.config = ConnectionConfig(
            host=host,
            port=port,
            path=path,
            auto_reconnect=auto_reconnect,
            reconnect_delay=reconnect_delay,
            secret_key=secret_key,
        )
        self._connection = ConnectionManager(self.config)
        self._default_timeout = 60.0
        # 密钥：用于多插件路由，指定目标插件
        self._secret_key = secret_key
        # 网站域名到标签页 ID 的映射表
        self._site_tab_map: Dict[str, int] = {}

        # 注册扩展连接事件：当扩展连接时重新初始化 tab 映射
        self._connection.on_event("extension_connected", self._on_extension_connected)

    async def _on_extension_connected(self, params: dict) -> None:
        """扩展连接事件处理器，重新初始化 tab 映射"""
        logger.info("[SilentAgentClient] 扩展已连接，重新初始化 tab 映射")
        await self._init_site_tab_map()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ========== 连接管理 ==========

    async def connect(self) -> ConnectionInfo:
        """连接到服务器"""
        info = await self._connection.connect()
        # 连接成功后，尝试初始化 tab 映射
        await self._init_site_tab_map()
        return info

    async def _init_site_tab_map(self) -> None:
        """
        初始化网站域名到标签页的映射

        通过浏览器扩展获取所有标签页，然后根据 URL 提取域名，
        建立域名到 tabId 的映射关系。
        """
        if not self.is_connected:
            return

        try:
            # 调用 browser_control 的 query_tabs 获取所有标签页
            result = await self.execute_tool("browser_control", {
                "action": "query_tabs",
                "params": {}
            }, timeout=10)

            if result.get("success") and result.get("data"):
                tabs = result["data"]
                for tab in tabs:
                    tab_id = tab.get("tabId")
                    url = tab.get("url", "")
                    if not url or not tab_id:
                        continue

                    # 提取域名
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        domain = parsed.netloc.lower()
                        # 移除端口号
                        if ":" in domain:
                            domain = domain.split(":")[0]
                        # 忽略空白域名
                        if not domain:
                            continue
                        # 存储域名到 tabId 的映射
                        self._site_tab_map[domain] = tab_id
                        logger.info(f"[_init_site_tab_map] 映射域名 '{domain}' -> tabId {tab_id}")
                    except Exception as e:
                        logger.warning(f"[_init_site_tab_map] 解析域名失败: {url}, {e}")

                logger.info(f"[_init_site_tab_map] 初始化完成，共 {len(self._site_tab_map)} 个映射")
            else:
                logger.warning(f"[_init_site_tab_map] 获取标签页失败: {result}")

        except Exception as e:
            logger.warning(f"[_init_site_tab_map] 初始化失败: {e}")

    async def disconnect(self, reason: str = "用户断开") -> None:
        """断开连接"""
        await self._connection.disconnect(reason)

    async def reconnect(self, max_attempts: int = 10) -> ConnectionInfo:
        """重新连接"""
        return await self._connection.reconnect(max_attempts)

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connection.is_connected

    @property
    def is_extension_connected(self) -> bool:
        """扩展是否已连接"""
        return self._connection.is_extension_connected

    @property
    def connection_info(self) -> ConnectionInfo:
        """获取连接信息"""
        return self._connection.info

    # ========== 网站 Tab 映射管理 ==========

    def set_site_tab(self, site_domain: str, tab_id: int) -> None:
        """
        设置网站域名对应的标签页

        Args:
            site_domain: 网站域名（如 xiaohongshu.com）
            tab_id: 标签页 ID
        """
        self._site_tab_map[site_domain] = tab_id

    def get_site_tab(self, site_domain: str) -> Optional[int]:
        """
        获取网站域名对应的标签页

        支持精确匹配和模糊匹配（如 www.xiaohongshu.com 匹配 xiaohongshu.com）

        Args:
            site_domain: 网站域名（如 xiaohongshu.com 或 www.xiaohongshu.com）

        Returns:
            标签页 ID，如果没有返回 None
        """
        # 精确匹配
        if site_domain in self._site_tab_map:
            return self._site_tab_map[site_domain]

        # 模糊匹配：移除前缀后匹配（如 www.xiaohongshu.com -> xiaohongshu.com）
        domain = site_domain.lower()
        # 尝试去掉常见前缀
        for prefix in ("www.", "m.", "mobile.", "shop.", "creator.", "creatorcenter.", "work."):
            if domain.startswith(prefix):
                base_domain = domain[len(prefix):]
                if base_domain in self._site_tab_map:
                    return self._site_tab_map[base_domain]
                # 继续尝试多级前缀
                for prefix2 in ("www.", "m.", "mobile.", "shop."):
                    if base_domain.startswith(prefix2):
                        base_domain2 = base_domain[len(prefix2):]
                        if base_domain2 in self._site_tab_map:
                            return self._site_tab_map[base_domain2]

        return None

    def clear_site_tab(self, site_domain: str) -> None:
        """清除网站域名对应的标签页"""
        if site_domain in self._site_tab_map:
            del self._site_tab_map[site_domain]

    async def refresh_site_tabs(self) -> Dict[str, int]:
        """
        刷新网站域名到标签页的映射

        重新从浏览器获取所有标签页并更新映射表

        Returns:
            新的域名到 tabId 的映射字典
        """
        self._site_tab_map.clear()
        await self._init_site_tab_map()
        return self._site_tab_map

    @property
    def site_tab_map(self) -> Dict[str, int]:
        """获取当前网站域名到标签页的映射（只读副本）"""
        return dict(self._site_tab_map)

    @property
    def tools(self) -> List[str]:
        """获取可用工具列表"""
        return self._connection.extension_tools

    # ========== 事件处理 ==========

    def on_connected(self, handler: Callable) -> None:
        """连接成功事件"""
        self._connection.on_event("connected", handler)

    def on_disconnected(self, handler: Callable) -> None:
        """断开连接事件"""
        self._connection.on_event("disconnected", handler)

    def on_extension_connected(self, handler: Callable) -> None:
        """扩展连接事件"""
        self._connection.on_event("extension_connected", handler)

    def on_extension_disconnected(self, handler: Callable) -> None:
        """扩展断开事件"""
        self._connection.on_event("extension_disconnected", handler)

    def on_error(self, handler: Callable) -> None:
        """错误事件"""
        self._connection.on_event("error", handler)

    def on_event(self, event_type: str, handler: Callable) -> None:
        """通用事件注册"""
        self._connection.on_event(event_type, handler)

    # ========== 工具执行 ==========

    def _execute_business_tool(
        self,
        name: str,
        params: Dict[str, Any] = None,
        context: 'ExecutionContext' = None
    ) -> Any:
        """
        直接执行 Python 业务工具（不经过 relay_server）

        Args:
            name: 工具名称
            params: 工具参数
            context: 执行上下文（包含 client 等资源）

        Returns:
            工具执行结果

        Note:
            统一从 context 获取 secret_key，业务工具可通过 context.secret_key 访问
            无需每个业务工具单独实现获取逻辑
        """
        if name not in BUSINESS_TOOLS:
            raise ValueError(f"未知业务工具: {name}")

        # 统一获取 secret_key：优先使用 context 中的，否则使用默认的
        secret_key = getattr(context, 'secret_key', None) if context else None
        if not secret_key:
            secret_key = self._secret_key

        # 确保 context 有 secret_key 属性（供业务工具使用）
        if context and not hasattr(context, 'secret_key'):
            context.secret_key = secret_key

        module_path, func_name = BUSINESS_TOOLS[name]

        # 动态导入模块和函数
        import importlib
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        # 调用函数 - 如果函数签名包含 context，则传递
        try:
            import inspect
            sig = inspect.signature(func)
            if 'context' in sig.parameters:
                # 函数支持 context 参数
                result = func(**(params or {}), context=context)
            elif 'tab_id' in sig.parameters or 'params' in sig.parameters:
                # 对于 BusinessTool 类型，传递 params 和 context
                # 检查是否是 Tool 类（有 execute 方法）
                if hasattr(func, 'execute') or hasattr(func, '_execute_core'):
                    # 这是一个 Tool 类实例或类方法，需要通过 execute 调用
                    # 使用便捷函数方式
                    tool_func = getattr(module, func_name, None)
                    if tool_func and callable(tool_func):
                        # 检查是否是便捷函数（直接返回结果）
                        result = tool_func(**(params or {}))
                    else:
                        result = func(**(params or {}))
                else:
                    result = func(**(params or {}))
            else:
                result = func(**(params or {}))
            # 自动转换 Result 对象为标准格式
            return self._convert_result(result)
        except Exception as e:
            raise ConnectionError(f"业务工具执行失败: {e}")

    def _convert_result(self, result: Any) -> Dict[str, Any]:
        """
        将 Result 对象转换为标准 API 格式
        """
        from src.core.result import Result, Error

        # 如果不是 Result 对象，直接返回
        if not isinstance(result, Result):
            return result

        # Result 已经是标准格式
        if result.success:
            return {
                "success": True,
                "data": result.data,
                "error": None,
            }
        else:
            # 处理错误情况
            error_msg = None
            if result.error:
                if isinstance(result.error, Error):
                    error_msg = result.error.message
                elif isinstance(result.error, dict):
                    error_msg = result.error.get("message", str(result.error))
                else:
                    error_msg = str(result.error)
            return {
                "success": False,
                "data": None,
                "error": error_msg or "执行失败",
            }

    async def execute_tool(
        self,
        name: str,
        params: Dict[str, Any] = None,
        timeout: float = None,
        context: 'ExecutionContext' = None,
        secret_key: str = None
    ) -> Dict[str, Any]:
        """
        执行工具

        Args:
            name: 工具名称
                - 业务工具 (xhs_*): 直接在 Python 端执行
                - 浏览器工具 (browser.*, chrome_*): 通过 relay_server 发到 extension 执行
            params: 工具参数
            timeout: 超时时间（秒）
            context: 可选的执行上下文（用于业务工具访问浏览器）
            secret_key: 可选的密钥，用于指定目标插件（不传则使用默认密钥）

        Returns:
            工具执行结果

        Raises:
            ConnectionError: 连接错误
            TimeoutError: 执行超时
            ValueError: 未知工具
        """
        # 1. 检查是否是业务工具（Python 端直接执行）
        if name in BUSINESS_TOOLS:
            try:
                # 将 self（client）注入到 context 中，方便业务工具访问浏览器
                if context is None:
                    from src.tools.base import ExecutionContext
                    context = ExecutionContext()
                # 将当前 client 注入到 context 中
                context.client = self

                result = self._execute_business_tool(name, params, context)
                if asyncio.iscoroutine(result):
                    result = await result
                # 转换为标准格式
                return self._format_result(name, result)
            except Exception as e:
                raise ConnectionError(f"业务工具执行失败: {e}")

        # 2. 浏览器工具需要通过 relay_server 发到 extension
        # 注意：业务工具不需要 connection，浏览器工具需要

        # 检查 relay_server 连接
        if not self.is_connected:
            raise DisconnectedError("未连接到 relay_server，请先启动 relay_server.py")

        # 将 API 工具名映射到扩展工具名
        extension_tool_name = self.TOOL_NAME_MAP.get(name, name)

        # 确定使用的密钥：优先使用传入的参数，否则使用默认密钥
        used_key = secret_key or self._secret_key

        # 发送执行请求 (使用 relay_server 期望的格式)
        timeout = timeout or self._default_timeout
        request = {
            "method": "executeTool",
            "params": {
                "name": extension_tool_name,
                "args": params or {},
                "timeout": timeout,
                "secretKey": used_key,  # 传递密钥用于多插件路由
            },
        }

        try:
            response = await self._connection.send_and_wait(request, timeout)
            logger.debug(f"[API] (execute_tool) 接收到工具执行结果: {response}")
            return response
        except asyncio.TimeoutError:
            raise TimeoutError(f"工具执行超时: {name}", {"tool": name, "timeout": timeout})

    def _format_result(self, name: str, result: Any) -> Dict[str, Any]:
        """
        格式化工具结果为标准格式

        Args:
            name: 工具名称
            result: 原始结果

        Returns:
            标准格式结果
        """
        if isinstance(result, dict):
            # 已经是字典格式
            if "success" in result:
                return result
            # 转换为标准格式
            return {
                "success": not result.get("isError", False),
                "data": result.get("data") or result.get("content"),
                "error": result.get("error") or (result.get("content")[0].get("text") if result.get("content") else None),
            }
        else:
            return {
                "success": True,
                "data": str(result),
                "error": None,
            }

    # ========== 便捷方法 ==========

    async def click(
        self,
        selector: str,
        text: str = None,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """点击元素"""
        kwargs = {"selector": selector, "timeout": int(timeout * 1000)}
        if text:
            kwargs["text"] = text
        return await self.execute_tool("chrome_click", kwargs)

    async def fill(
        self,
        selector: str,
        value: str,
        method: str = "set",
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """填充表单"""
        return await self.execute_tool("chrome_fill", {
            "selector": selector,
            "value": value,
            "method": method,
            "timeout": int(timeout * 1000),
        })

    async def navigate(
        self,
        url: str,
        new_tab: bool = True,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """导航到 URL"""
        return await self.execute_tool("chrome_navigate", {
            "url": url,
            "newTab": new_tab,
            "timeout": int(timeout * 1000),
        })

    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all_elements: bool = False,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """提取数据"""
        return await self.execute_tool("chrome_extract_data", {
            "selector": selector,
            "attribute": attribute,
            "all": all_elements,
            "timeout": int(timeout * 1000),
        })

    async def inject(
        self,
        code: str,
        world: str = "MAIN"
    ) -> Any:
        """注入脚本"""
        return await self.execute_tool("inject_script", {
            "code": code,
            "world": world,
        })

    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None
    ) -> Dict[str, Any]:
        """滚动页面"""
        kwargs = {"direction": direction, "amount": amount}
        if selector:
            kwargs["selector"] = selector
        return await self.execute_tool("chrome_scroll", kwargs)

    async def screenshot(
        self,
        img_format: str = "png",
        quality: int = 80
    ) -> Dict[str, Any]:
        """截图"""
        return await self.execute_tool("chrome_screenshot", {
            "format": format,
            "quality": quality,
        })

    async def wait_for(
        self,
        selector: str,
        count: int = 1,
        timeout: float = 60.0
    ) -> Dict[str, Any]:
        """等待元素"""
        return await self.execute_tool("chrome_wait_elements", {
            "selector": selector,
            "count": count,
            "timeout": int(timeout * 1000),
        })

    async def get_a11y_tree(
        self,
        limit: int = 100
    ) -> Dict[str, Any]:
        """获取无障碍树"""
        return await self.execute_tool("a11y_tree", {
            "action": "get_tree",
            "limit": limit,
        })

    async def get_focused_element(self) -> Dict[str, Any]:
        """获取聚焦元素"""
        return await self.execute_tool("a11y_tree", {
            "action": "get_focused",
        })

    async def execute_tool_async(
        self,
        name: str,
        params: Dict[str, Any] = None
    ) -> str:
        """
        异步执行工具（不等待结果）

        Args:
            name: 工具名称
            params: 工具参数

        Returns:
            请求 ID
        """
        if not self.is_connected:
            raise DisconnectedError("未连接到服务器")

        import uuid
        request_id = str(uuid.uuid4())

        request = {
            "id": request_id,
            "type": "execute",
            "method": name,
            "params": {"name": name, "args": params or {}},
        }

        await self._connection.send(request)
        return request_id

    async def wait_for_result(self, request_id: str, timeout: float = 60.0) -> Dict[str, Any]:
        """等待异步执行结果"""
        # 创建一个 future 来等待结果
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._connection._pending_responses[request_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._connection._pending_responses.pop(request_id, None)
            raise TimeoutError(f"等待结果超时: {request_id}")

    # ========== 代理方法 ==========

    async def call_tool(self, name: str, timeout: float = 60, secret_key: str = None, **args) -> Any:
        """
        代理调用浏览器工具

        Args:
            name: 工具名称
            timeout: 超时秒数
            secret_key: 可选的密钥，用于指定目标插件
            **args: 工具参数

        Returns:
            工具执行结果
        """
        # 确定使用的密钥
        used_key = secret_key or self._secret_key

        # 使用 relay_server 期望的格式
        message = {
            "method": "executeTool",
            "params": {
                "name": name,
                "args": args,
                "timeout": timeout,
                "secretKey": used_key,  # 传递密钥用于多插件路由
            }
        }
        result = await self._connection.send_and_wait(
            message=message,
            timeout=timeout + 5
        )
        return result

    # ========== 资源管理 ==========

    async def close(self) -> None:
        """关闭客户端"""
        await self._connection.close()

    def __repr__(self) -> str:
        state = "connected" if self.is_connected else "disconnected"
        ext = "ext_connected" if self.is_extension_connected else "ext_disconnected"
        return f"<SilentAgentClient: {state}, {ext}, tools={len(self.tools)}>"


# ========== 便捷函数 ==========

async def create_client(
    host: str = "127.0.0.1",
    port: int = 18792,
    auto_reconnect: bool = True,
) -> SilentAgentClient:
    """创建并连接客户端"""
    client = SilentAgentClient(host=host, port=port, auto_reconnect=auto_reconnect)
    await client.connect()
    return client


async def execute_tool(
    name: str,
    params: Dict[str, Any] = None,
    timeout: float = None
) -> Dict[str, Any]:
    """
    便捷工具执行函数

    Args:
        name: 工具名称
        params: 工具参数
        timeout: 超时时间（秒）

    Returns:
        工具执行结果
    """
    client = SilentAgentClient()
    try:
        await client.connect()
        return await client.execute_tool(name, params, timeout)
    finally:
        await client.close()


def execute_business_tool(name: str, params: Dict[str, Any] = None) -> Any:
    """
    同步便捷函数 - 直接执行业务工具（无需连接 relay_server）

    专门用于执行小红书等业务工具，这些工具在 Python 端实现，
    不需要浏览器扩展连接。

    Args:
        name: 工具名称 (如 "xhs_check_login_status")
        params: 工具参数

    Returns:
        工具执行结果

    Example:
        result = execute_business_tool("xhs_check_login_status", {})
    """
    import importlib

    if name not in BUSINESS_TOOLS:
        raise ValueError(f"未知业务工具: {name}")

    module_path, func_name = BUSINESS_TOOLS[name]
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)

    # 调用函数
    try:
        if asyncio.iscoroutinefunction(func):
            result = asyncio.run(func(**(params or {})))
        else:
            result = func(**(params or {}))

        # 自动转换 Result 对象为标准格式
        return _convert_result(result)
    except Exception as e:
        raise ConnectionError(f"业务工具执行失败: {e}")


def _convert_result(result: Any) -> Dict[str, Any]:
    """
    将 Result 对象转换为标准 API 格式

    Args:
        result: Result 对象或其他类型

    Returns:
        标准格式字典 {success, data, error}
    """
    from src.core.result import Result, Error

    # 如果不是 Result 对象，直接返回
    if not isinstance(result, Result):
        return result

    # Result 已经是标准格式
    if result.success:
        return {
            "success": True,
            "data": result.data,
            "error": None,
        }
    else:
        # 处理错误情况
        error_msg = None
        if result.error:
            if isinstance(result.error, Error):
                error_msg = result.error.message
            elif isinstance(result.error, dict):
                error_msg = result.error.get("message", str(result.error))
            else:
                error_msg = str(result.error)
        return {
            "success": False,
            "data": None,
            "error": error_msg or "执行失败",
        }


__all__ = [
    "SilentAgentClient",
    "create_client",
    "execute_tool",
    "execute_business_tool",
    "BUSINESS_TOOLS",
]
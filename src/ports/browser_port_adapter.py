"""
浏览器端口适配器

将现有的 BrowserClient 适配为 BrowserPort 接口。
用于在不修改原有客户端的情况下实现依赖倒置。
"""

from typing import Any, Dict, List, Optional

from src.browser.base import BrowserClient
from src.core.result import Result, Error, ErrorCode


class BrowserPortAdapter(BrowserClient):
    """
    浏览器端口适配器

    将 BrowserClient 适配为 BrowserPort 接口。
    负责将 Dict 返回类型转换为 Result 类型。
    """

    def __init__(self, client: BrowserClient):
        """
        初始化适配器

        Args:
            client: 现有的 BrowserClient 实例
        """
        self._client = client

    # ========== 连接状态代理 ==========

    @property
    def is_connected(self) -> bool:
        """代理到客户端的连接状态"""
        return self._client.is_connected

    async def connect(self) -> None:
        """代理到客户端的连接"""
        return await self._client.connect()

    async def close(self) -> None:
        """代理到客户端的关闭"""
        return await self._client.close()

    # ========== 页面导航 ==========

    async def navigate(self, url: str, **kwargs) -> Result[dict]:
        """导航到 URL"""
        try:
            result = await self._client.navigate(url, **kwargs)
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    # ========== 元素操作 ==========

    async def click(self, selector: str, **kwargs) -> Result[dict]:
        """点击元素"""
        try:
            result = await self._client.click(selector, **kwargs)
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    async def fill(self, selector: str, value: str, **kwargs) -> Result[dict]:
        """填充表单"""
        try:
            result = await self._client.fill(selector, value, **kwargs)
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all: bool = False,
        **kwargs
    ) -> Result[dict]:
        """提取页面数据"""
        try:
            result = await self._client.extract(selector, attribute, all)
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    async def wait_for(
        self,
        selector: str,
        timeout: int = 30000,
        **kwargs
    ) -> Result[dict]:
        """等待元素出现"""
        try:
            result = await self._client.wait_for(
                selector,
                count=kwargs.get("count", 1),
                timeout=timeout / 1000  # 转换为秒
            )
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    # ========== JavaScript ==========

    async def evaluate(self, script: str, **kwargs) -> Result[dict]:
        """执行 JavaScript"""
        try:
            world = kwargs.get("world", "MAIN")
            result = await self._client.inject(script, world)
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    # ========== 截图 ==========

    async def screenshot(self, **kwargs) -> Result[dict]:
        """截取页面截图"""
        try:
            format = kwargs.get("format", "png")
            result = await self._client.screenshot(format)
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    # ========== 无障碍树 ==========

    async def get_a11y_tree(self, **kwargs) -> Result[dict]:
        """获取无障碍树"""
        try:
            action = kwargs.get("action", "get_tree")
            limit = kwargs.get("limit", 100)
            tab_id = kwargs.get("tab_id")
            result = await self._client.get_a11y_tree(action, limit, tab_id)
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    # ========== 标签页操作 ==========

    async def get_active_tab(self) -> Result[dict]:
        """获取当前活动标签页"""
        try:
            result = await self._client.get_active_tab()
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    async def close_tab(self, tab_id: int) -> Result[dict]:
        """关闭标签页"""
        try:
            result = await self._client.close_tab(tab_id)
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    async def list_tabs(self) -> Result[List[dict]]:
        """列出所有标签页"""
        try:
            result = await self._client.list_tabs()
            return Result.ok(result)
        except Exception as e:
            return Result.fail(Error.from_exception(e, recoverable=True))

    # ========== 额外方法代理 ==========

    def __getattr__(self, name: str) -> Any:
        """代理其他方法到客户端"""
        return getattr(self._client, name)


__all__ = ["BrowserPortAdapter"]

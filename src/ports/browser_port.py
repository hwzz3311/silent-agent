"""
浏览器操作端口

定义浏览器操作的抽象接口，实现依赖倒置原则。
用于在不同浏览器客户端实现之间切换（Puppeteer/Extension/Hybrid）。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.core.result import Result


class BrowserPort(ABC):
    """
    浏览器操作端口

    定义浏览器操作的抽象接口，所有浏览器客户端实现必须实现此接口。
    用于实现依赖倒置，使工具层不直接依赖具体客户端实现。
    """

    # ========== 连接状态 ==========

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """是否已连接"""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """连接到浏览器"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass

    # ========== 页面导航 ==========

    @abstractmethod
    async def navigate(self, url: str, **kwargs) -> Result[dict]:
        """
        导航到 URL

        Args:
            url: 目标 URL
            **kwargs: 额外参数 (如 new_tab)

        Returns:
            Result[dict]: 导航结果
        """
        pass

    # ========== 元素操作 ==========

    @abstractmethod
    async def click(self, selector: str, **kwargs) -> Result[dict]:
        """
        点击元素

        Args:
            selector: CSS 选择器
            **kwargs: 额外参数 (如 text, timeout)

        Returns:
            Result[dict]: 点击结果
        """
        pass

    @abstractmethod
    async def fill(self, selector: str, value: str, **kwargs) -> Result[dict]:
        """
        填充表单

        Args:
            selector: CSS 选择器
            value: 填充值
            **kwargs: 额外参数 (如 method)

        Returns:
            Result[dict]: 填充结果
        """
        pass

    @abstractmethod
    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all: bool = False,
        **kwargs
    ) -> Result[dict]:
        """
        提取页面数据

        Args:
            selector: CSS 选择器
            attribute: 提取属性 (text/html/value)
            all: 是否提取所有匹配元素
            **kwargs: 额外参数

        Returns:
            Result[dict]: 提取结果
        """
        pass

    @abstractmethod
    async def wait_for(
        self,
        selector: str,
        timeout: int = 30000,
        **kwargs
    ) -> Result[dict]:
        """
        等待元素出现

        Args:
            selector: CSS 选择器
            timeout: 超时时间（毫秒）
            **kwargs: 额外参数 (如 count)

        Returns:
            Result[dict]: 等待结果
        """
        pass

    # ========== JavaScript ==========

    @abstractmethod
    async def evaluate(self, script: str, **kwargs) -> Result[dict]:
        """
        在页面中执行 JavaScript

        Args:
            script: JavaScript 代码
            **kwargs: 额外参数 (如 world)

        Returns:
            Result[dict]: 执行结果
        """
        pass

    # ========== 滚动和键盘 ==========

    @abstractmethod
    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None,
        **kwargs
    ) -> Result[dict]:
        """
        滚动页面

        Args:
            direction: 滚动方向 (up/down/left/right)
            amount: 滚动距离（像素）
            selector: 目标元素选择器（可选）
            **kwargs: 额外参数

        Returns:
            Result[dict]: 滚动结果
        """
        pass

    @abstractmethod
    async def keyboard(self, keys: str, selector: str = None, **kwargs) -> Result[dict]:
        """
        模拟键盘输入

        Args:
            keys: 按键序列
            selector: 目标元素选择器（可选）
            **kwargs: 额外参数

        Returns:
            Result[dict]: 输入结果
        """
        pass

    # ========== 截图 ==========

    @abstractmethod
    async def screenshot(self, **kwargs) -> Result[dict]:
        """
        截取页面截图

        Args:
            **kwargs: 额外参数 (如 format)

        Returns:
            Result[dict]: 截图结果
        """
        pass

    # ========== 无障碍树 ==========

    @abstractmethod
    async def get_a11y_tree(self, **kwargs) -> Result[dict]:
        """
        获取无障碍树

        Args:
            **kwargs: 额外参数 (如 action, limit, tab_id)

        Returns:
            Result[dict]: 无障碍树数据
        """
        pass

    # ========== 标签页操作 (可选) ==========

    @abstractmethod
    async def get_active_tab(self) -> Result[dict]:
        """获取当前活动标签页"""
        pass

    @abstractmethod
    async def close_tab(self, tab_id: int) -> Result[dict]:
        """关闭标签页"""
        pass

    @abstractmethod
    async def list_tabs(self) -> Result[List[dict]]:
        """列出所有标签页"""
        pass


__all__ = ["BrowserPort"]

"""
浏览器客户端抽象基类

定义浏览器操作的统一接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BrowserClientError(Exception):
    """浏览器客户端错误"""
    pass


class BrowserClient(ABC):
    """
    浏览器客户端抽象基类

    所有浏览器客户端实现必须继承此类。
    """

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

    # ========== 页面操作 ==========

    @abstractmethod
    async def navigate(self, url: str, new_tab: bool = True) -> Dict[str, Any]:
        """
        导航到 URL

        Args:
            url: 目标 URL
            new_tab: 是否在新标签页打开

        Returns:
            导航结果
        """
        pass

    @abstractmethod
    async def click(self, selector: str, text: str = None, timeout: float = 5) -> Dict[str, Any]:
        """
        点击元素

        Args:
            selector: CSS 选择器
            text: 元素文本（可选，用于精确定位）
            timeout: 超时时间（秒）

        Returns:
            点击结果
        """
        pass

    @abstractmethod
    async def fill(self, selector: str, value: str, method: str = "set") -> Dict[str, Any]:
        """
        填充表单

        Args:
            selector: CSS 选择器
            value: 填充值
            method: 填充方式 (set/input)

        Returns:
            填充结果
        """
        pass

    @abstractmethod
    async def extract(
        self,
        selector: str,
        attribute: str = "text",
        all: bool = False
    ) -> Dict[str, Any]:
        """
        提取页面数据

        Args:
            selector: CSS 选择器
            attribute: 提取属性 (text/html/value)
            all: 是否提取所有匹配元素

        Returns:
            提取结果
        """
        pass

    @abstractmethod
    async def inject(self, code: str, world: str = "MAIN") -> Dict[str, Any]:
        """
        在页面中执行 JavaScript

        Args:
            code: JavaScript 代码
            world: 执行世界 (MAIN/ISOLATED)

        Returns:
            执行结果
        """
        pass

    @abstractmethod
    async def screenshot(self, format: str = "png") -> Dict[str, Any]:
        """
        截取页面截图

        Args:
            format: 图片格式 (png/jpeg)

        Returns:
            截图结果（base64 或文件路径）
        """
        pass

    @abstractmethod
    async def scroll(
        self,
        direction: str = "down",
        amount: int = 300,
        selector: str = None
    ) -> Dict[str, Any]:
        """
        滚动页面

        Args:
            direction: 滚动方向 (up/down/left/right)
            amount: 滚动距离（像素）
            selector: 目标元素选择器（可选）

        Returns:
            滚动结果
        """
        pass

    @abstractmethod
    async def wait_for(
        self,
        selector: str,
        count: int = 1,
        timeout: float = 60
    ) -> Dict[str, Any]:
        """
        等待元素出现

        Args:
            selector: CSS 选择器
            count: 期望元素数量
            timeout: 超时时间（秒）

        Returns:
            等待结果
        """
        pass

    @abstractmethod
    async def keyboard(self, keys: str, selector: str = None) -> Dict[str, Any]:
        """
        模拟键盘输入

        Args:
            keys: 按键序列
            selector: 目标元素选择器（可选）

        Returns:
            输入结果
        """
        pass

    # ========== 无障碍树 ==========

    @abstractmethod
    async def get_a11y_tree(
        self,
        action: str = "get_tree",
        limit: int = 100,
        tab_id: int = None
    ) -> Dict[str, Any]:
        """
        获取无障碍树

        Args:
            action: 操作类型 (get_tree/get_focused/get_node/query)
            limit: 返回节点数量限制
            tab_id: 标签页 ID（可选）

        Returns:
            无障碍树数据
        """
        pass

    # ========== 标签页操作 ==========

    @abstractmethod
    async def get_active_tab(self) -> Dict[str, Any]:
        """获取当前活动标签页"""
        pass

    @abstractmethod
    async def close_tab(self, tab_id: int) -> Dict[str, Any]:
        """关闭标签页"""
        pass

    @abstractmethod
    async def list_tabs(self) -> List[Dict[str, Any]]:
        """列出所有标签页"""
        pass


__all__ = ["BrowserClient", "BrowserClientError"]
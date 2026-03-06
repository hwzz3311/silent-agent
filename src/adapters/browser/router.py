"""
浏览器路由策略

定义操作到客户端的映射规则。
"""

from typing import Optional, Set
from abc import ABC, abstractmethod


class BrowserRoutingStrategy(ABC):
    """路由策略基类"""

    @abstractmethod
    def select_client(self, operation: str, puppeteer, extension):
        """选择执行操作的客户端"""
        pass


class DefaultRoutingStrategy(BrowserRoutingStrategy):
    """默认路由策略"""

    # 操作分类
    PUPPETEER_ONLY: Set[str] = {"navigate", "screenshot", "get_a11y_tree", "list_tabs", "get_active_tab"}
    EXTENSION_PREFERRED: Set[str] = {"click", "fill", "extract", "scroll", "keyboard", "wait_for"}
    FLEXIBLE: Set[str] = {"evaluate", "inject"}

    def select_client(self, operation: str, puppeteer, extension):
        # 优先策略
        if operation in self.PUPPETEER_ONLY and puppeteer:
            return puppeteer
        if operation in self.EXTENSION_PREFERRED and extension:
            return extension
        if operation in self.FLEXIBLE:
            # 灵活选择：优先 extension
            if extension:
                return extension
            if puppeteer:
                return puppeteer
        # 回退：谁可用用谁
        return puppeteer or extension


__all__ = ["BrowserRoutingStrategy", "DefaultRoutingStrategy"]

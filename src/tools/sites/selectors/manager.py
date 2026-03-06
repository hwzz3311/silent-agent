"""
选择器管理器

提供选择器的注册和获取功能（精简版）。
"""

from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass


class SelectorType(str, Enum):
    """选择器类型"""
    CSS = "css"
    XPATH = "xpath"
    ID = "id"
    CLASS = "class"
    NAME = "name"
    TEXT = "text"
    ATTRIBUTE = "attribute"
    COMPOUND = "compound"


@dataclass
class SelectorInfo:
    """选择器信息"""
    selector: str
    selector_type: SelectorType = SelectorType.CSS
    description: Optional[str] = None


@dataclass
class SelectorTestResult:
    """选择器测试结果"""
    selector: str
    success: bool
    found_count: int = 0
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    is_recommended: bool = False


class SelectorManager:
    """选择器管理器（精简版）"""

    def __init__(self, site_name: str, default_timeout: int = 5000):
        self._site_name = site_name
        self.default_timeout = default_timeout
        self._selectors: Dict[str, SelectorInfo] = {}
        self._selector_cache: Dict[str, str] = {}

    @property
    def site_name(self) -> str:
        return self._site_name

    @site_name.setter
    def site_name(self, value: str):
        self._site_name = value

    def register(
        self,
        name: str,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        description: str = None
    ) -> SelectorInfo:
        """注册选择器"""
        info = SelectorInfo(
            selector=selector,
            selector_type=selector_type,
            description=description,
        )
        self._selectors[name] = info
        self._invalidate_cache(name)
        return info

    def register_with_info(self, name: str, info: SelectorInfo) -> SelectorInfo:
        """使用 SelectorInfo 对象注册选择器"""
        self._selectors[name] = info
        self._invalidate_cache(name)
        return info

    def register_many(self, selectors: Dict[str, SelectorInfo]) -> int:
        """批量注册选择器"""
        count = 0
        for name, info in selector.items():
            if self.register_with_info(name, info):
                count += 1
        return count

    def unregister(self, name: str) -> bool:
        """注销选择器"""
        if name in self._selectors:
            del self._selectors[name]
            self._invalidate_cache(name)
            return True
        return False

    def get(self, name: str) -> Optional[SelectorInfo]:
        """获取选择器信息"""
        return self._selectors.get(name)

    def get_selector(self, name: str) -> Optional[str]:
        """获取选择器字符串"""
        if name in self._selector_cache:
            return self._selector_cache[name]
        info = self._selectors.get(name)
        if info:
            self._selector_cache[name] = info.selector
            return info.selector
        return None

    def get_all(self) -> Dict[str, SelectorInfo]:
        """获取所有选择器"""
        return self._selectors.copy()

    def get_by_type(self, selector_type: SelectorType) -> Dict[str, SelectorInfo]:
        """获取指定类型的所有选择器"""
        return {
            name: info
            for name, info in self._selectors.items()
            if info.selector_type == selector_type
        }

    def validate_selector(self, selector: str) -> bool:
        """验证选择器格式是否有效"""
        import re
        if not selector or not isinstance(selector, str):
            return False
        if "javascript:" in selector.lower():
            return False
        valid_patterns = [r'^[.#\w\[\]\-=":\s,>+~*()]+$']
        for pattern in valid_patterns:
            if re.match(pattern, selector):
                return True
        return False

    async def test_selector(self, selector: str, test_fn) -> SelectorTestResult:
        """测试选择器"""
        import time
        start_time = time.time()
        try:
            found_count = test_fn(selector)
            execution_time = (time.time() - start_time) * 1000
            return SelectorTestResult(
                selector=selector,
                success=found_count > 0,
                found_count=found_count,
                execution_time_ms=execution_time
            )
        except Exception as e:
            return SelectorTestResult(
                selector=selector,
                success=False,
                error_message=str(e)
            )

    def _invalidate_cache(self, name: str):
        """使缓存失效"""
        self._selector_cache.pop(name, None)

    def clear_cache(self):
        """清空缓存"""
        self._selector_cache.clear()

    def clear_all(self):
        """清空所有数据"""
        self._selectors.clear()
        self._selector_cache.clear()

    def export_selectors(self) -> Dict[str, Dict]:
        """导出所有选择器"""
        return {
            name: {"selector": info.selector, "selector_type": info.selector_type, "description": info.description}
            for name, info in self._selectors.items()
        }

    def import_selectors(self, selector: Dict[str, Dict]) -> int:
        """导入选择器"""
        count = 0
        for name, data in selector.items():
            info = SelectorInfo(**data)
            if self.register_with_info(name, info):
                count += 1
        return count


class GlobalSelectorManager:
    """全局选择器管理器"""

    def __init__(self):
        self._managers: Dict[str, SelectorManager] = {}

    def get_manager(self, site_name: str) -> SelectorManager:
        """获取网站选择器管理器"""
        if site_name not in self._managers:
            self._managers[site_name] = SelectorManager(site_name)
        return self._managers[site_name]

    def register_site(self, site_name: str, default_selectors: Dict[str, SelectorInfo]) -> int:
        """注册网站及其默认选择器"""
        manager = self.get_manager(site_name)
        return manager.register_many(default_selectors)

    def list_sites(self) -> List[str]:
        """列出所有网站"""
        return list(self._managers.keys())


_global_selector_manager: Optional[GlobalSelectorManager] = None


def get_selector_manager() -> GlobalSelectorManager:
    """获取选择器管理器（支持依赖注入）"""
    global _global_selector_manager
    if _global_selector_manager is None:
        _global_selector_manager = GlobalSelectorManager()
    return _global_selector_manager


def set_selector_manager(manager: GlobalSelectorManager) -> None:
    """注入管理器（用于测试）"""
    global _global_selector_manager
    _global_selector_manager = manager


def reset_selector_manager() -> None:
    """重置管理器（用于测试清理）"""
    global _global_selector_manager
    _global_selector_manager = None


__all__ = [
    "SelectorType",
    "SelectorInfo",
    "SelectorTestResult",
    "SelectorManager",
    "GlobalSelectorManager",
    "get_selector_manager",
    "set_selector_manager",
    "reset_selector_manager",
]

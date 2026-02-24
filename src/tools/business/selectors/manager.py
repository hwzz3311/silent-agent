"""
选择器管理器

提供选择器的版本管理、自动降级和验证功能。
"""

from typing import TYPE_CHECKING, Dict, Optional, Any, List, Callable
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
import time

if TYPE_CHECKING:
    pass


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


class SelectorStatus(str, Enum):
    """选择器状态"""
    ACTIVE = "active"        # 活跃中
    DEPRECATED = "deprecated"  # 已废弃
    FAILED = "failed"        # 失败
    TESTING = "testing"      # 测试中


class SelectorInfo(BaseModel):
    """
    选择器信息

    Attributes:
        selector: CSS/XPath 选择器
        selector_type: 选择器类型
        status: 当前状态
        success_count: 成功次数
        failure_count: 失败次数
        last_success: 最后成功时间
        last_failure: 最后失败时间
        page_type: 适用页面类型
        priority: 优先级（数值越小优先级越高）
        alternatives: 备用选择器列表
        description: 描述
    """
    selector: str
    selector_type: SelectorType = SelectorType.CSS
    status: SelectorStatus = SelectorStatus.ACTIVE
    success_count: int = 0
    failure_count: int = 0
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    page_type: str = "all"
    priority: int = 100
    alternatives: List[str] = []
    description: Optional[str] = None
    site_name: Optional[str] = None

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    @property
    def reliability_score(self) -> float:
        """计算可靠性分数（考虑时间衰减）"""
        # 基础成功率
        base_score = self.success_rate

        # 时间衰减因子（24小时内为1，超过后逐渐降低）
        if self.last_success:
            hours_since = (time.time() - self.last_success) / 3600
            time_factor = max(0.5, 1.0 - hours_since / 168)  # 7天后最低0.5
        else:
            time_factor = 0.5

        # 最终分数
        return base_score * time_factor


class SelectorTestResult(BaseModel):
    """选择器测试结果"""
    selector: str
    success: bool
    found_count: int = 0
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    is_recommended: bool = False


class SelectorManager:
    """
    选择器管理器

    功能:
    1. 选择器版本管理
    2. 选择器自动降级
    3. 选择器缓存
    4. 选择器验证
    5. 性能统计

    Usage:
        manager = SelectorManager("xiaohongshu")

        # 注册选择器
        manager.register("feed_card", SelectorInfo(
            selector=".feed-card",
            alternatives=[".note-item", "[data-testid='feed-card']"]
        ))

        # 获取选择器（自动降级）
        selector = manager.get_with_fallback("feed_card")

        # 记录使用结果
        manager.record_success(selector)
        # 或
        manager.record_failure(selector, error)
    """

    def __init__(
        self,
        site_name: str,
        default_timeout: int = 5000
    ):
        """
        初始化选择器管理器

        Args:
            site_name: 网站名称
            default_timeout: 默认超时时间
        """
        self.site_name = site_name
        self.default_timeout = default_timeout

        # 选择器存储
        self._selectors: Dict[str, SelectorInfo] = {}
        self._selector_cache: Dict[str, str] = {}
        self._fallback_chains: Dict[str, List[str]] = {}

        # 统计
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "fallback_count": 0,
        }

    @property
    def site_name(self) -> str:
        """获取网站名称"""
        return self._site_name

    @site_name.setter
    def site_name(self, value: str):
        self._site_name = value

    # ========== 注册方法 ==========

    def register(
        self,
        name: str,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        page_type: str = "all",
        priority: int = 100,
        alternatives: List[str] = None,
        description: str = None
    ) -> SelectorInfo:
        """
        注册选择器

        Args:
            name: 选择器名称（唯一标识）
            selector: CSS 选择器
            selector_type: 选择器类型
            page_type: 适用页面类型
            priority: 优先级
            alternatives: 备用选择器列表
            description: 描述

        Returns:
            SelectorInfo: 选择器信息对象
        """
        info = SelectorInfo(
            selector=selector,
            selector_type=selector_type,
            page_type=page_type,
            priority=priority,
            alternatives=alternatives or [],
            description=description,
            site_name=self.site_name
        )

        # 注册选择器
        self._selectors[name] = info

        # 构建降级链
        self._build_fallback_chain(name, selector, alternatives)

        # 清空相关缓存
        self._invalidate_cache(name)

        return info

    def register_with_info(self, name: str, info: SelectorInfo) -> SelectorInfo:
        """
        使用 SelectorInfo 对象注册选择器

        Args:
            name: 选择器名称
            info: 选择器信息

        Returns:
            SelectorInfo: 选择器信息对象
        """
        info.site_name = self.site_name
        self._selectors[name] = info

        # 构建降级链
        self._build_fallback_chain(name, info.selector, info.alternatives)

        # 清空相关缓存
        self._invalidate_cache(name)

        return info

    def register_many(self, selectors: Dict[str, SelectorInfo]) -> int:
        """
        批量注册选择器

        Args:
            selectors: 选择器字典

        Returns:
            int: 注册数量
        """
        count = 0
        for name, info in selectors.items():
            if self.register_with_info(name, info):
                count += 1
        return count

    def unregister(self, name: str) -> bool:
        """
        注销选择器

        Args:
            name: 选择器名称

        Returns:
            bool: 是否成功
        """
        if name in self._selectors:
            del self._selectors[name]
            self._fallback_chains.pop(name, None)
            self._invalidate_cache(name)
            return True
        return False

    # ========== 获取方法 ==========

    def get(self, name: str) -> Optional[SelectorInfo]:
        """
        获取选择器信息

        Args:
            name: 选择器名称

        Returns:
            Optional[SelectorInfo]: 选择器信息，不存在返回 None
        """
        return self._selectors.get(name)

    def get_selector(self, name: str) -> Optional[str]:
        """
        获取选择器字符串

        Args:
            name: 选择器名称

        Returns:
            Optional[str]: 选择器字符串
        """
        # 先检查缓存
        if name in self._selector_cache:
            self._stats["cache_hits"] += 1
            return self._selector_cache[name]

        # 获取选择器
        info = self._selectors.get(name)
        if info:
            self._selector_cache[name] = info.selector
            return info.selector

        return None

    def get_with_fallback(
        self,
        name: str,
        allow_fallback: bool = True
    ) -> Optional[str]:
        """
        获取选择器（自动降级）

        如果主选择器失败，会尝试使用备用选择器。

        Args:
            name: 选择器名称
            allow_fallback: 是否允许降级

        Returns:
            Optional[str]: 选择器字符串
        """
        self._stats["total_requests"] += 1

        # 获取主选择器
        selector = self.get_selector(name)

        if selector:
            return selector

        # 尝试降级
        if allow_fallback:
            fallback = self._get_fallback(name)
            if fallback:
                self._stats["fallback_count"] += 1
                return fallback

        return None

    def get_all(self) -> Dict[str, SelectorInfo]:
        """
        获取所有选择器

        Returns:
            Dict[str, SelectorInfo]: 选择器字典
        """
        return self._selectors.copy()

    def get_by_page(self, page_type: str) -> Dict[str, SelectorInfo]:
        """
        获取指定页面类型的所有选择器

        Args:
            page_type: 页面类型

        Returns:
            Dict[str, SelectorInfo]: 选择器字典
        """
        return {
            name: info
            for name, info in self._selectors.items()
            if info.page_type in ("all", page_type)
        }

    def get_by_type(self, selector_type: SelectorType) -> Dict[str, SelectorInfo]:
        """
        获取指定类型的所有选择器

        Args:
            selector_type: 选择器类型

        Returns:
            Dict[str, SelectorInfo]: 选择器字典
        """
        return {
            name: info
            for name, info in self._selectors.items()
            if info.selector_type == selector_type
        }

    def get_by_priority(self, limit: int = 10) -> List[str]:
        """
        获取优先级最高的选择器名称

        Args:
            limit: 返回数量限制

        Returns:
            List[str]: 选择器名称列表
        """
        sorted_names = sorted(
            self._selectors.keys(),
            key=lambda n: self._selectors[n].priority
        )
        return sorted_names[:limit]

    # ========== 记录方法 ==========

    def record_success(self, selector: str, name: str = None) -> bool:
        """
        记录选择器使用成功

        Args:
            selector: 选择器字符串
            name: 选择器名称（可选）

        Returns:
            bool: 是否找到并更新
        """
        # 查找选择器
        if name:
            info = self._selectors.get(name)
        else:
            info = self._find_by_selector(selector)

        if info:
            info.success_count += 1
            info.last_success = time.time()
            info.status = SelectorStatus.ACTIVE

            # 如果是备用选择器成功的，提升优先级
            if selector != info.selector and info.fallback_chain:
                info.priority = min(info.priority, 50)

            return True

        return False

    def record_failure(
        self,
        selector: str,
        error: Exception = None,
        name: str = None
    ) -> bool:
        """
        记录选择器使用失败

        Args:
            selector: 选择器字符串
            error: 异常信息
            name: 选择器名称（可选）

        Returns:
            bool: 是否找到并更新
        """
        # 查找选择器
        if name:
            info = self._selectors.get(name)
        else:
            info = self._find_by_selector(selector)

        if info:
            info.failure_count += 1
            info.last_failure = time.time()

            # 检查是否应该标记为废弃
            if info.success_count > 0 and info.failure_count > 3:
                rate = info.success_count / (info.success_count + info.failure_count)
                if rate < 0.3:  # 成功率低于30%
                    info.status = SelectorStatus.DEPRECATED

            return True

        return False

    def record_test_result(
        self,
        name: str,
        result: SelectorTestResult
    ) -> bool:
        """
        记录测试结果

        Args:
            name: 选择器名称
            result: 测试结果

        Returns:
            bool: 是否成功
        """
        info = self._selectors.get(name)
        if not info:
            return False

        if result.success:
            info.success_count += 1
            info.last_success = time.time()
            info.status = SelectorStatus.ACTIVE
        else:
            info.failure_count += 1
            info.last_failure = time.time()

            # 如果测试失败且不是推荐的，尝试备用的
            if not result.is_recommended and info.alternatives:
                for alt in info.alternatives:
                    if alt != selector and self._selectors.get(alt):
                        # 标记备用选择器需要测试
                        pass

        return True

    # ========== 验证方法 ==========

    def validate_selector(self, selector: str) -> bool:
        """
        验证选择器格式是否有效

        Args:
            selector: CSS 选择器

        Returns:
            bool: 是否有效
        """
        import re

        # 基本格式检查
        if not selector or not isinstance(selector, str):
            return False

        # 检查是否包含危险字符
        if "javascript:" in selector.lower():
            return False

        # 检查基本 CSS 选择器格式
        # 简单的正则检查，不是完全准确
        valid_patterns = [
            r'^[.#\w\[\]\-=":\s,>+~*()]+$',  # 通用 CSS
        ]

        for pattern in valid_patterns:
            if re.match(pattern, selector):
                return True

        return False

    async def test_selector(
        self,
        selector: str,
        test_fn: Callable[[str], bool]
    ) -> SelectorTestResult:
        """
        测试选择器

        Args:
            selector: 选择器字符串
            test_fn: 测试函数，接收选择器返回是否找到元素

        Returns:
            SelectorTestResult: 测试结果
        """
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

    def get_reliability_score(self, name: str) -> float:
        """
        获取选择器可靠性分数

        Args:
            name: 选择器名称

        Returns:
            float: 可靠性分数 (0-1)
        """
        info = self._selectors.get(name)
        if info:
            return info.reliability_score
        return 0.0

    # ========== 统计方法 ==========

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_selectors = len(self._selectors)
        total_success = sum(s.success_count for s in self._selectors.values())
        total_failure = sum(s.failure_count for s in self._selectors.values())

        return {
            "site_name": self.site_name,
            "total_selectors": total_selectors,
            "total_requests": self._stats["total_requests"],
            "cache_hits": self._stats["cache_hits"],
            "fallback_count": self._stats["fallback_count"],
            "cache_hit_rate": (
                self._stats["cache_hits"] / self._stats["total_requests"]
                if self._stats["total_requests"] > 0 else 0
            ),
            "total_success": total_success,
            "total_failure": total_failure,
            "overall_success_rate": (
                total_success / (total_success + total_failure)
                if (total_success + total_failure) > 0 else 1.0
            ),
        }

    def list_reliability_ranking(self, limit: int = 10) -> List[tuple]:
        """
        获取可靠性排名

        Args:
            limit: 返回数量限制

        Returns:
            List[tuple]: [(name, reliability_score), ...]
        """
        rankings = [
            (name, info.reliability_score)
            for name, info in self._selectors.items()
        ]
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings[:limit]

    # ========== 内部方法 ==========

    def _build_fallback_chain(
        self,
        name: str,
        primary: str,
        alternatives: List[str]
    ):
        """
        构建降级链

        Args:
            name: 选择器名称
            primary: 主选择器
            alternatives: 备用选择器列表
        """
        chain = [primary]
        for alt in alternatives:
            if alt not in chain:
                chain.append(alt)
        self._fallback_chains[name] = chain

    def _get_fallback(self, name: str) -> Optional[str]:
        """
        获取备用选择器

        Args:
            name: 选择器名称

        Returns:
            Optional[str]: 备用选择器
        """
        chain = self._fallback_chains.get(name, [])
        if len(chain) > 1:
            return chain[1]  # 返回第一个备用
        return None

    def _find_by_selector(self, selector: str) -> Optional[SelectorInfo]:
        """
        通过选择器字符串查找选择器信息

        Args:
            selector: 选择器字符串

        Returns:
            Optional[SelectorInfo]: 选择器信息
        """
        for info in self._selectors.values():
            if info.selector == selector or selector in info.alternatives:
                return info
        return None

    def _invalidate_cache(self, name: str):
        """
        使缓存失效

        Args:
            name: 选择器名称
        """
        self._selector_cache.pop(name, None)

    def clear_cache(self):
        """清空缓存"""
        self._selector_cache.clear()
        self._stats["cache_hits"] = 0

    def clear_all(self):
        """清空所有数据"""
        self._selectors.clear()
        self._selector_cache.clear()
        self._fallback_chains.clear()
        self._stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "fallback_count": 0,
        }

    def export_selectors(self) -> Dict[str, Dict[str, Any]]:
        """
        导出所有选择器

        Returns:
            Dict[str, Dict]: 选择器字典
        """
        # Pydantic v2+ uses model_dump, v1 uses dict
        def dump_info(info):
            if hasattr(info, 'model_dump'):
                return info.model_dump()
            else:
                return info.dict()

        return {
            name: dump_info(info)
            for name, info in self._selectors.items()
        }

    def import_selectors(self, selectors: Dict[str, Dict[str, Any]]) -> int:
        """
        导入选择器

        Args:
            selectors: 选择器字典

        Returns:
            int: 导入数量
        """
        count = 0
        for name, data in selectors.items():
            info = SelectorInfo(**data)
            if self.register_with_info(name, info):
                count += 1
        return count


class GlobalSelectorManager:
    """
    全局选择器管理器

    管理所有网站的选择器。
    """

    _instance: Optional['GlobalSelectorManager'] = None
    _managers: Dict[str, SelectorManager] = {}

    def __new__(cls) -> 'GlobalSelectorManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_managers'):
            self._managers = {}

    def get_manager(self, site_name: str) -> SelectorManager:
        """
        获取网站选择器管理器

        Args:
            site_name: 网站名称

        Returns:
            SelectorManager: 选择器管理器
        """
        if site_name not in self._managers:
            self._managers[site_name] = SelectorManager(site_name)
        return self._managers[site_name]

    def register_site(self, site_name: str, default_selectors: Dict[str, SelectorInfo]) -> int:
        """
        注册网站及其默认选择器

        Args:
            site_name: 网站名称
            default_selectors: 默认选择器

        Returns:
            int: 注册数量
        """
        manager = self.get_manager(site_name)
        return manager.register_many(default_selectors)

    def list_sites(self) -> List[str]:
        """
        列出所有网站

        Returns:
            List[str]: 网站名称列表
        """
        return list(self._managers.keys())


# 全局选择器管理器实例
global_selector_manager = GlobalSelectorManager()


__all__ = [
    "SelectorType",
    "SelectorStatus",
    "SelectorInfo",
    "SelectorTestResult",
    "SelectorManager",
    "GlobalSelectorManager",
    "global_selector_manager",
]
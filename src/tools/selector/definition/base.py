"""
选择器基类定义

提供通用选择器结构和选择器集合格式化逻辑。
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class BasePageSelectors(BaseModel):
    """
    基础页面选择器

    所有网站页面选择器的基类，定义通用字段。
    子类应继承并扩展此基础选择器。
    """
    pass


class BaseExtraSelectors(BaseModel):
    """
    基础备用选择器

    当主选择器失败时使用的备用选择器列表。
    """
    pass


class BaseSelectorSet(BaseModel):
    """
    基础选择器集合

    包含主选择器和备用选择器的通用逻辑。
    所有网站特定的 SelectorSet 应继承此类。
    """

    page: BasePageSelectors = Field(
        default_factory=BasePageSelectors,
        description="页面选择器"
    )
    extra: BaseExtraSelectors = Field(
        default_factory=BaseExtraSelectors,
        description="备用选择器"
    )

    # 备用链映射
    fallback_chains: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="选择器备用链"
    )

    class Config:
        arbitrary_types_allowed = True

    def get_selector(self, name: str) -> Optional[str]:
        """
        获取选择器（支持嵌套路径，如 'page.feed_card'）

        Args:
            name: 选择器名称，支持点分路径

        Returns:
            Optional[str]: 选择器值
        """
        parts = name.split('.')

        # 导航到正确的嵌套对象
        current = self
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                # 尝试从 fallback_chains 获取
                return self.fallback_chains.get(name)

        if isinstance(current, str):
            return current
        if isinstance(current, list) and len(current) > 0:
            return current[0]
        return None

    def get_with_fallback(
        self,
        primary: str,
        fallback_key: str
    ) -> Optional[str]:
        """
        获取主选择器，失败时使用备用选择器

        Args:
            primary: 主选择器名称
            fallback_key: 备用选择器 key（对应 extra 里的字段名）

        Returns:
            Optional[str]: 选择器值
        """
        # 获取主选择器
        primary_selector = self.get_selector(primary)
        if primary_selector:
            return primary_selector

        # 获取备用选择器 - 从 extra 对象的属性获取
        if hasattr(self.extra, fallback_key):
            fallback_value = getattr(self.extra, fallback_key)
            if isinstance(fallback_value, list):
                for selector in fallback_value:
                    if self._validate_selector(selector):
                        return selector

        # 也支持从 fallback_chains 获取
        fallback_selectors = self.fallback_chains.get(fallback_key, [])
        for selector in fallback_selectors:
            if self._validate_selector(selector):
                return selector

        return None

    def _validate_selector(self, selector: str) -> bool:
        """
        验证选择器格式

        Args:
            selector: 选择器字符串

        Returns:
            bool: 是否有效
        """
        if not selector or len(selector) < 2:
            return False

        # 检查危险字符
        dangerous = ["javascript:", "data:", "<", ">"]
        for d in dangerous:
            if d in selector.lower():
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "page": {
                k: v if not hasattr(v, 'model_dump') else v.model_dump()
                for k, v in self.page.__dict__.items()
            },
            "extra": {
                k: v if not hasattr(v, 'model_dump') else v.model_dump()
                for k, v in self.extra.__dict__.items()
            },
            "fallback_chains": self.fallback_chains
        }


__all__ = [
    "BasePageSelectors",
    "BaseExtraSelectors",
    "BaseSelectorSet",
]

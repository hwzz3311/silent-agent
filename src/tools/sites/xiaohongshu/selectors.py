"""
小红书选择器定义

提供小红书各页面的 CSS 选择器定义。
继承通用搜索选择器。
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from ..selectors import (
    BaseSelectorSet,
    CommonSearchSelectors,
)


class XHSPageSelectors(CommonSearchSelectors, BaseModel):
    """
    小红书页面选择器

    继承通用搜索选择器。
    """

    # ========== 首页选择器 ==========
    feed_container: str = ".feeds-container, .feed-list, [data-testid='feed-container']"
    feed_card: str = ".feed-card, .note-item, [data-testid='feed-card']"

    # ========== 笔记详情页选择器 ==========
    detail_images: List[str] = Field(
        default_factory=list,
        description="笔记详情图片选择器列表"
    )


class XHSExtraSelectors(BaseModel):
    """
    小红书备用选择器

    可扩展小红书特定备用选择器。
    """
    pass


class XHSSelectorSet(BaseSelectorSet):
    """
    小红书完整选择器集合

    包含主选择器和备用选择器。
    """

    page: XHSPageSelectors = Field(
        default_factory=XHSPageSelectors,
        description="页面选择器"
    )
    extra: XHSExtraSelectors = Field(
        default_factory=XHSExtraSelectors,
        description="备用选择器"
    )


# 预定义的 XHS 选择器集合实例
xhs_default_selectors = XHSSelectorSet()


# 便捷函数：获取小红书默认选择器
def get_xhs_selectors() -> XHSSelectorSet:
    """获取小红书默认选择器集合"""
    return xhs_default_selectors


__all__ = [
    "XHSPageSelectors",
    "XHSExtraSelectors",
    "XHSSelectorSet",
    "xhs_default_selectors",
    "get_xhs_selectors",
]

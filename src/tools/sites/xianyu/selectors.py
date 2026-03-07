"""
闲鱼选择器定义

提供闲鱼各页面的 CSS 选择器定义。
继承通用搜索选择器。
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from ..selectors import (
    BaseSelectorSet,
    CommonSearchSelectors,
)


class XianyuPageSelector(CommonSearchSelectors, BaseModel):
    """
    闲鱼页面选择器

    继承通用搜索选择器并扩展闲鱼特定选择器。
    """

    # ========== 首页/商品列表选择器 ==========
    goods_container: str = ".goods-container, .goods-list, [data-testid='goods-container']"
    goods_card: str = ".goods-card, .item-goods, [data-testid='goods-card']"
    goods_title: str = ".goods-title, .item-title, [data-testid='goods-title']"
    goods_cover: str = ".goods-cover, .item-cover, [data-testid='goods-cover']"
    goods_price: str = ".goods-price, .item-price, [data-testid='goods-price']"
    goods_author: str = ".goods-author, .seller-name, [data-testid='goods-author']"
    goods_likes: str = ".goods-likes, .like-count, [data-testid='goods-likes']"
    goods_comments: str = ".goods-comments, .comment-count, [data-testid='goods-comments']"
    goods_collect_button: str = ".collect-btn, .favorite-btn, [data-testid='collect-btn']"
    goods_like_button: str = ".like-btn, [data-testid='like-btn']"
    goods_share_button: str = ".share-btn, [data-testid='share-btn']"
    goods_message_button: str = ".message-btn, .contact-btn, [data-testid='message-btn']"

    # ========== 商品详情页选择器 ==========
    detail_seller: str = ".detail-seller, [data-testid='detail-seller']"
    detail_seller_info: str = ".seller-info, [data-testid='seller-info']"
    detail_message_button: str = ".message-btn, [data-testid='message-btn']"

    # ========== 用户主页/店铺选择器 ==========
    profile_goods: str = ".profile-goods, .goods-tab, [data-testid='profile-goods']"
    profile_goods_card: str = ".profile-goods-card, [data-testid='profile-goods-card']"

    # ========== 发布商品选择器 ==========
    publish_price_input: str = ".price-input, [data-testid='price-input']"

    # ========== 消息页选择器 ==========
    message_container: str = ".message-page, .chat-list, [data-testid='message-container']"
    message_list: str = ".message-list, .chat-list, [data-testid='message-list']"
    message_item: str = ".message-item, .chat-item, [data-testid='message-item']"
    message_input: str = ".message-input, [contenteditable='true'], [data-testid='message-input']"
    message_send: str = ".message-send, .send-btn, [data-testid='message-send']"

    # ========== 订单页选择器 ==========
    order_container: str = ".order-page, .order-list, [data-testid='order-container']"
    order_card: str = ".order-card, .order-item, [data-testid='order-card']"
    order_status: str = ".order-status, [data-testid='order-status']"
    order_goods: str = ".order-goods, [data-testid='order-goods']"


class XianyuExtraSelector(BaseModel):
    """
    闲鱼备用选择器

    可扩展闲鱼特定备用选择器。
    """
    pass


class XianyuSelectorSet(BaseSelectorSet):
    """
    闲鱼完整选择器集合

    包含主选择器和备用选择器。
    """

    page: XianyuPageSelector = Field(
        default_factory=XianyuPageSelector,
        description="页面选择器"
    )
    extra: XianyuExtraSelector = Field(
        default_factory=XianyuExtraSelector,
        description="备用选择器"
    )


# 预定义的闲鱼选择器集合实例
xianyu_default_selectors = XianyuSelectorSet()


# 便捷函数：获取闲鱼默认选择器
def get_xianyu_selectors() -> XianyuSelectorSet:
    """获取闲鱼默认选择器集合"""
    return xianyu_default_selectors


__all__ = [
    "XianyuPageSelector",
    "XianyuExtraSelector",
    "XianyuSelectorSet",
    "xianyu_default_selectors",
    "get_xianyu_selectors",
]

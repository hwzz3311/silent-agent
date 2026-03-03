"""
闲鱼选择器定义

提供闲鱼各页面的 CSS 选择器定义。
继承通用选择器并扩展闲鱼特定选择器。
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field

from ..selectors import (
    BaseSelectorSet,
    CommonPaginationSelectors,
    CommonModalSelectors,
    CommonSearchSelectors,
    CommonFeedSelectors,
    CommonDetailSelectors,
    CommonProfileSelectors,
    CommonPublishSelectors,
    CommonExtraSelectors,
)


class XianyuPageSelectors(BaseModel):
    """
    闲鱼页面选择器

    按页面类型组织的选择器集合。
    继承通用选择器并扩展闲鱼特定选择器。
    """

    # ========== 通用分页选择器 ==========
    next_page_button: str = CommonPaginationSelectors.model_fields["next_page_button"].default
    infinite_scroll_container: str = CommonPaginationSelectors.model_fields["infinite_scroll_container"].default
    page_indicator: str = CommonPaginationSelectors.model_fields["page_indicator"].default

    # ========== 首页/商品列表选择器 ==========
    goods_container: str = CommonFeedSelectors.model_fields["feed_container"].default
    goods_card: str = CommonFeedSelectors.model_fields["feed_card"].default
    goods_title: str = CommonFeedSelectors.model_fields["feed_title"].default
    goods_cover: str = CommonFeedSelectors.model_fields["feed_cover"].default
    goods_price: str = CommonFeedSelectors.model_fields["feed_price"].default
    goods_author: str = CommonFeedSelectors.model_fields["feed_author"].default
    goods_likes: str = CommonFeedSelectors.model_fields["feed_likes"].default
    goods_comments: str = CommonFeedSelectors.model_fields["feed_comments"].default
    goods_collect_button: str = CommonFeedSelectors.model_fields["feed_save_button"].default
    goods_like_button: str = CommonFeedSelectors.model_fields["feed_like_button"].default
    goods_share_button: str = CommonFeedSelectors.model_fields["feed_share_button"].default
    goods_message_button: str = CommonFeedSelectors.model_fields["feed_comment_button"].default

    # ========== 商品详情页选择器 ==========
    detail_container: str = CommonDetailSelectors.model_fields["detail_container"].default
    detail_title: str = CommonDetailSelectors.model_fields["detail_title"].default
    detail_content: str = CommonDetailSelectors.model_fields["detail_content"].default
    detail_images: List[str] = Field(
        default_factory=list,
        description="商品详情图片选择器列表"
    )
    detail_image: str = CommonDetailSelectors.model_fields["detail_image"].default
    detail_price: str = CommonDetailSelectors.model_fields["detail_price"].default
    detail_likes: str = CommonDetailSelectors.model_fields["detail_likes"].default
    detail_comments: str = CommonDetailSelectors.model_fields["detail_comments"].default
    detail_comment_input: str = CommonDetailSelectors.model_fields["detail_comment_input"].default
    detail_comment_submit: str = CommonDetailSelectors.model_fields["detail_comment_submit"].default
    detail_seller: str = CommonDetailSelectors.model_fields["detail_author"].default
    detail_seller_info: str = CommonDetailSelectors.model_fields["detail_author_info"].default
    detail_follow_button: str = CommonDetailSelectors.model_fields["detail_follow_button"].default
    detail_message_button: str = CommonDetailSelectors.model_fields["detail_message_button"].default

    # ========== 用户主页/店铺选择器 ==========
    profile_container: str = CommonProfileSelectors.model_fields["profile_container"].default
    profile_avatar: str = CommonProfileSelectors.model_fields["profile_avatar"].default
    profile_name: str = CommonProfileSelectors.model_fields["profile_name"].default
    profile_description: str = CommonProfileSelectors.model_fields["profile_description"].default
    profile_followers: str = CommonProfileSelectors.model_fields["profile_followers"].default
    profile_goods: str = CommonProfileSelectors.model_fields["profile_notes"].default
    profile_tab: str = CommonProfileSelectors.model_fields["profile_tab"].default
    profile_goods_card: str = CommonProfileSelectors.model_fields["profile_note_card"].default

    # ========== 搜索页选择器 ==========
    search_container: str = CommonSearchSelectors.model_fields["search_container"].default
    search_input: str = CommonSearchSelectors.model_fields["search_input"].default
    search_button: str = CommonSearchSelectors.model_fields["search_button"].default
    search_result: str = CommonSearchSelectors.model_fields["search_result"].default
    search_no_result: str = CommonSearchSelectors.model_fields["search_no_result"].default
    search_filter: str = CommonSearchSelectors.model_fields["search_filter"].default
    search_filter_dropdown: str = CommonSearchSelectors.model_fields["search_filter_dropdown"].default
    search_suggestion: str = CommonSearchSelectors.model_fields["search_suggestion"].default

    # ========== 发布商品选择器 ==========
    publish_button: str = CommonPublishSelectors.model_fields["publish_button"].default
    publish_page: str = CommonPublishSelectors.model_fields["publish_page"].default
    publish_title_input: str = CommonPublishSelectors.model_fields["publish_title_input"].default
    publish_content_area: str = CommonPublishSelectors.model_fields["publish_content_area"].default
    publish_price_input: str = CommonPublishSelectors.model_fields["publish_price_input"].default
    publish_image_upload: str = CommonPublishSelectors.model_fields["publish_image_upload"].default
    publish_submit: str = CommonPublishSelectors.model_fields["publish_submit"].default
    publish_cancel: str = CommonPublishSelectors.model_fields["publish_cancel"].default
    publish_image_preview: str = CommonPublishSelectors.model_fields["publish_image_preview"].default

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

    # ========== 弹窗选择器 ==========
    modal_overlay: str = CommonModalSelectors.model_fields["modal_overlay"].default
    modal_container: str = CommonModalSelectors.model_fields["modal_container"].default
    confirm_button: str = CommonModalSelectors.model_fields["confirm_button"].default
    cancel_button: str = CommonModalSelectors.model_fields["cancel_button"].default
    close_button: str = CommonModalSelectors.model_fields["close_button"].default
    dialog_title: str = CommonModalSelectors.model_fields["dialog_title"].default
    dialog_body: str = CommonModalSelectors.model_fields["dialog_body"].default


class XianyuExtraSelectors(BaseModel):
    """
    闲鱼备用选择器

    当主选择器失败时使用的备用选择器列表。
    """

    # 通用备用选择器
    generic_container: List[str] = CommonExtraSelectors.model_fields["generic_container"].default
    goods_card_alternatives: List[str] = CommonExtraSelectors.model_fields["feed_card_alternatives"].default
    detail_container_alternatives: List[str] = CommonExtraSelectors.model_fields["detail_container_alternatives"].default
    login_button_alternatives: List[str] = CommonExtraSelectors.model_fields["login_button_alternatives"].default


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

"""
通用选择器定义

所有网站共享的选择器，包括分页、弹窗、搜索等通用场景。
"""

from typing import List
from pydantic import BaseModel, Field

from .base import BasePageSelectors, BaseExtraSelectors


class CommonPaginationSelectors(BaseModel):
    """
    通用分页选择器

    所有列表类页面共享的分页选择器。
    """

    next_page_button: str = ".next-btn, .load-more, [data-testid='load-more']"
    infinite_scroll_container: str = ".feed-list, .goods-list, .infinite-scroll, [data-testid='infinite-scroll']"
    page_indicator: str = ".page-indicator, .pagination, [data-testid='page-indicator']"


class CommonModalSelectors(BaseModel):
    """
    通用弹窗/对话框选择器

    所有页面共享的弹窗相关选择器。
    """

    modal_overlay: str = ".modal-overlay, .overlay, .el-overlay"
    modal_container: str = ".modal-container, .el-dialog, [data-testid='modal']"
    confirm_button: str = ".confirm-btn, .el-button--primary, [data-testid='confirm']"
    cancel_button: str = ".cancel-btn, .el-button--default, [data-testid='cancel']"
    close_button: str = ".close-btn, .el-dialog__close, [data-testid='close']"
    dialog_title: str = ".dialog-title, .el-dialog__title, [data-testid='dialog-title']"
    dialog_body: str = ".dialog-body, .el-dialog__body, [data-testid='dialog-body']"


class CommonSearchSelectors(BaseModel):
    """
    通用搜索选择器

    所有搜索页面共享的选择器。
    """

    search_container: str = ".search-page, .search-result, [data-testid='search-page']"
    search_input: str = ".search-input, [contenteditable='true'], [data-testid='search-input']"
    search_button: str = ".search-btn, .search-icon, [data-testid='search-btn']"
    search_result: str = ".search-result-item, [data-testid='search-result']"
    search_no_result: str = ".no-result, .empty-result, [data-testid='no-result']"
    search_filter: str = ".search-filter, .filter-item, [data-testid='search-filter']"
    search_filter_dropdown: str = ".filter-dropdown, [data-testid='filter-dropdown']"
    search_suggestion: str = ".search-suggestion, [data-testid='search-suggestion']"


class CommonFeedSelectors(BaseModel):
    """
    通用信息流/列表选择器

    首页信息流和列表页共享的选择器。
    """

    # 容器和卡片
    feed_container: str = ".feeds-container, .feed-list, .goods-container, .goods-list, [data-testid='feed-container']"
    feed_card: str = ".feed-card, .note-item, .goods-card, .item-goods, [data-testid='feed-card']"

    # 卡片内容
    feed_title: str = ".feed-title, .note-title, .goods-title, .item-title, [data-testid='feed-title']"
    feed_cover: str = ".feed-cover, .note-cover, .goods-cover, .item-cover, [data-testid='feed-cover']"
    feed_price: str = ".feed-price, .goods-price, .item-price, [data-testid='feed-price']"

    # 作者/卖家
    feed_author: str = ".feed-author, .note-author, .goods-author, .seller-name, [data-testid='feed-author']"
    feed_author_avatar: str = ".author-avatar, .seller-avatar, [data-testid='author-avatar']"

    # 互动数据
    feed_likes: str = ".feed-likes, .like-count, .goods-likes, .like-count, [data-testid='feed-likes']"
    feed_comments: str = ".feed-comments, .comment-count, .goods-comments, .comment-count, [data-testid='feed-comments']"
    feed_collects: str = ".feed-collects, .collect-count, [data-testid='feed-collects']"

    # 互动按钮
    feed_save_button: str = ".save-btn, .collect-btn, .collect-btn, [data-testid='save-btn']"
    feed_like_button: str = ".like-btn, [data-testid='like-btn']"
    feed_share_button: str = ".share-btn, [data-testid='share-btn']"
    feed_comment_button: str = ".comment-btn, .message-btn, [data-testid='comment-btn']"


class CommonDetailSelectors(BaseModel):
    """
    通用详情页选择器

    商品/笔记详情页共享的选择器。
    """

    detail_container: str = ".note-detail, .goods-detail, .detail-page, [data-testid='detail-container']"
    detail_title: str = ".note-title, .goods-title, [data-testid='detail-title']"
    detail_content: str = ".note-content, .goods-desc, .description, [data-testid='detail-content']"
    detail_image: str = ".note-image, .goods-image, .detail-image, [data-testid='detail-image']"
    detail_images: List[str] = Field(
        default_factory=list,
        description="详情图片选择器列表"
    )
    detail_price: str = ".detail-price, .price, [data-testid='detail-price']"

    # 互动数据
    detail_likes: str = ".detail-likes, .likes-count, [data-testid='detail-likes']"
    detail_collects: str = ".detail-collects, .collects-count, [data-testid='detail-collects']"
    detail_comments: str = ".detail-comments, .comments-section, [data-testid='detail-comments']"

    # 评论输入
    detail_comment_input: str = ".comment-input, [contenteditable='true'], [data-testid='comment-input']"
    detail_comment_submit: str = ".comment-submit, .send-comment, [data-testid='comment-submit']"

    # 作者/卖家
    detail_author: str = ".detail-author, .detail-seller, [data-testid='detail-author']"
    detail_author_info: str = ".author-info, .seller-info, [data-testid='author-info']"
    detail_follow_button: str = ".follow-btn, [data-testid='follow-btn']"
    detail_message_button: str = ".message-btn, [data-testid='message-btn']"


class CommonProfileSelectors(BaseModel):
    """
    通用用户主页选择器

    用户/店铺主页共享的选择器。
    """

    profile_container: str = ".user-profile, .shop-profile, .profile-page, [data-testid='profile-container']"
    profile_avatar: str = ".profile-avatar, .shop-avatar, [data-testid='profile-avatar']"
    profile_name: str = ".profile-name, .shop-name, .nickname, [data-testid='profile-name']"
    profile_description: str = ".profile-description, .shop-desc, .user-desc, [data-testid='profile-description']"
    profile_followers: str = ".profile-followers, .fans-count, .followers-count, [data-testid='profile-followers']"
    profile_following: str = ".profile-following, .following-count, [data-testid='profile-following']"
    profile_likes: str = ".profile-likes, .likes-count, [data-testid='profile-likes']"

    # 笔记/商品列表
    profile_notes: str = ".profile-notes, .notes-tab, .profile-goods, .goods-tab, [data-testid='profile-notes']"
    profile_tab: str = ".profile-tab, .tab-item, [data-testid='profile-tab']"
    profile_note_card: str = ".profile-note-card, .profile-goods-card, [data-testid='profile-note-card']"

    # 子标签页
    profile_notes_tab: str = ".notes-tab, [data-testid='notes-tab']"
    profile_likes_tab: str = ".likes-tab, [data-testid='likes-tab']"
    profile_collections_tab: str = ".collections-tab, [data-testid='collections-tab']"


class CommonPublishSelectors(BaseModel):
    """
    通用发布页选择器

    发布笔记/商品页共享的选择器。
    """

    publish_button: str = ".publish-btn, .create-note, .sell-btn, [data-testid='publish-button']"
    publish_page: str = ".publish-page, .editor-page, [data-testid='publish-page']"
    publish_title_input: str = ".title-input, [data-testid='title-input']"
    publish_content_area: str = ".content-area, [contenteditable='true'], [data-testid='content-area']"
    publish_price_input: str = ".price-input, [data-testid='price-input']"
    publish_image_upload: str = ".image-upload, .upload-btn, [data-testid='image-upload']"
    publish_video_upload: str = ".video-upload, .video-btn, [data-testid='video-upload']"
    publish_submit: str = ".publish-submit, .submit-btn, [data-testid='publish-submit']"
    publish_cancel: str = ".publish-cancel, .cancel-btn, [data-testid='publish-cancel']"
    publish_image_preview: str = ".image-preview, .preview-image, [data-testid='image-preview']"
    publish_video_preview: str = ".video-preview, .preview-video, [data-testid='video-preview']"


class CommonExtraSelectors(BaseModel):
    """
    通用备用选择器

    所有网站共享的备用选择器。
    """

    generic_container: List[str] = Field(
        default_factory=lambda: [
            "[data-testid]",
            ".el-container",
            ".main-container"
        ],
        description="通用容器备用选择器"
    )

    feed_card_alternatives: List[str] = Field(
        default_factory=lambda: [
            "[data-testid='feed-card']",
            "[data-testid='goods-card']",
            ".feed-item",
            ".note-item",
            ".goods-item",
            ".item-goods",
            ".card-item",
            "[class*='feed']",
            "[class*='note']",
            "[class*='goods']",
            "[class*='item']"
        ],
        description="信息流卡片备用选择器"
    )

    detail_container_alternatives: List[str] = Field(
        default_factory=lambda: [
            "[data-testid='note-detail']",
            "[data-testid='goods-detail']",
            ".note-detail-page",
            ".goods-detail-page",
            ".detail-container",
            "[class*='detail']",
            "[class*='note']",
            "[class*='goods']"
        ],
        description="详情页备用选择器"
    )

    login_button_alternatives: List[str] = Field(
        default_factory=lambda: [
            "[data-testid='login-btn']",
            ".login-btn",
            ".btn-login",
            "[class*='login']",
            "[text()*='登录']"
        ],
        description="登录按钮备用选择器"
    )


# 便捷函数：创建通用页面选择器
def create_common_page_selectors(
    pagination: bool = True,
    modal: bool = True,
    search: bool = True,
    feed: bool = True,
    detail: bool = True,
    profile: bool = True,
    publish: bool = True,
) -> type[BasePageSelectors]:
    """
    创建通用页面选择器类

    根据参数组合通用的选择器字段。
    """
    fields_definitions = {}

    if pagination:
        for name, value in CommonPaginationSelectors.model_fields.items():
            field_definition[name] = value
            field_definition[name] = value

    if modal:
        for name, value in CommonModalSelectors.model_fields.items():
            field_definition[name] = value

    if search:
        for name, value in CommonSearchSelectors.model_fields.items():
            field_definition[name] = value

    if feed:
        for name, value in CommonFeedSelectors.model_fields.items():
            field_definition[name] = value

    if detail:
        for name, value in CommonDetailSelectors.model_fields.items():
            field_definition[name] = value

    if profile:
        for name, value in CommonProfileSelectors.model_fields.items():
            field_definition[name] = value

    if publish:
        for name, value in CommonPublishSelectors.model_fields.items():
            field_definition[name] = value

    # 创建动态类
    return type(
        "CommonPageSelectors",
        (BasePageSelectors,),
        field_definition
    )


__all__ = [
    "CommonPaginationSelectors",
    "CommonModalSelectors",
    "CommonSearchSelectors",
    "CommonFeedSelectors",
    "CommonDetailSelectors",
    "CommonProfileSelectors",
    "CommonPublishSelectors",
    "CommonExtraSelectors",
    "create_common_page_selectors",
]

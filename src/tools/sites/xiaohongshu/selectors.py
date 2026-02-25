"""
小红书选择器定义

提供小红书各页面的 CSS 选择器定义。
"""

from typing import Optional, Dict, List
from pydantic import BaseModel, Field



class XHSPageSelectors(BaseModel):
    """
    小红书页面选择器

    按页面类型组织的选择器集合。
    """

    # ========== 通用分页选择器 ==========
    next_page_button: str = ".next-btn, .load-more, [data-testid='load-more']"
    infinite_scroll_container: str = ".feed-list, .infinite-scroll, [data-testid='infinite-scroll']"
    page_indicator: str = ".page-indicator, .pagination, [data-testid='page-indicator']"

    # ========== 首页选择器 ==========
    feed_container: str = ".feeds-container, .feed-list, [data-testid='feed-container']"
    feed_card: str = ".feed-card, .note-item, [data-testid='feed-card']"
    feed_title: str = ".feed-title, .note-title, [data-testid='feed-title']"
    feed_cover: str = ".feed-cover, .note-cover, [data-testid='feed-cover']"
    feed_author: str = ".feed-author, .note-author, [data-testid='feed-author']"
    feed_author_avatar: str = ".author-avatar, [data-testid='author-avatar']"
    feed_likes: str = ".feed-likes, .like-count, [data-testid='feed-likes']"
    feed_comments: str = ".feed-comments, .comment-count, [data-testid='feed-comments']"
    feed_collects: str = ".feed-collects, .collect-count, [data-testid='feed-collects']"
    feed_save_button: str = ".save-btn, .collect-btn, [data-testid='save-btn']"
    feed_like_button: str = ".like-btn, [data-testid='like-btn']"
    feed_share_button: str = ".share-btn, [data-testid='share-btn']"
    feed_comment_button: str = ".comment-btn, [data-testid='comment-btn']"

    # ========== 笔记详情页选择器 ==========
    detail_container: str = ".note-detail, .detail-page, [data-testid='note-detail']"
    detail_title: str = ".note-title, [data-testid='note-title']"
    detail_content: str = ".note-content, [data-testid='note-content']"
    detail_images: List[str] = Field(
        default_factory=list,
        description="笔记详情图片选择器列表"
    )
    detail_image: str = ".note-image, .detail-image, [data-testid='detail-image']"
    detail_likes: str = ".detail-likes, .likes-count, [data-testid='detail-likes']"
    detail_collects: str = ".detail-collects, .collects-count, [data-testid='detail-collects']"
    detail_comments: str = ".detail-comments, .comments-section, [data-testid='detail-comments']"
    detail_comment_input: str = ".comment-input, [contenteditable='true'], [data-testid='comment-input']"
    detail_comment_submit: str = ".comment-submit, .send-comment, [data-testid='comment-submit']"
    detail_author: str = ".detail-author, [data-testid='detail-author']"
    detail_author_info: str = ".author-info, [data-testid='author-info']"
    detail_follow_button: str = ".follow-btn, [data-testid='follow-btn']"

    # ========== 用户主页选择器 ==========
    profile_container: str = ".user-profile, .profile-page, [data-testid='user-profile']"
    profile_avatar: str = ".profile-avatar, [data-testid='profile-avatar']"
    profile_name: str = ".profile-name, .nickname, [data-testid='profile-name']"
    profile_description: str = ".profile-description, .user-desc, [data-testid='profile-description']"
    profile_followers: str = ".profile-followers, .followers-count, [data-testid='profile-followers']"
    profile_following: str = ".profile-following, .following-count, [data-testid='profile-following']"
    profile_likes: str = ".profile-likes, .likes-count, [data-testid='profile-likes']"
    profile_notes: str = ".profile-notes, .notes-tab, [data-testid='profile-notes']"
    profile_tab: str = ".profile-tab, .tab-item, [data-testid='profile-tab']"
    profile_note_card: str = ".profile-note-card, [data-testid='profile-note-card']"
    profile_notes_tab: str = ".notes-tab, [data-testid='notes-tab']"
    profile_likes_tab: str = ".likes-tab, [data-testid='likes-tab']"
    profile_collections_tab: str = ".collections-tab, [data-testid='collections-tab']"

    # ========== 搜索页选择器 ==========
    search_container: str = ".search-page, .search-result, [data-testid='search-page']"
    search_input: str = ".search-input, [contenteditable='true'], [data-testid='search-input']"
    search_button: str = ".search-btn, .search-icon, [data-testid='search-btn']"
    search_result: str = ".search-result-item, [data-testid='search-result']"
    search_no_result: str = ".no-result, .empty-result, [data-testid='no-result']"
    search_filter: str = ".search-filter, .filter-item, [data-testid='search-filter']"
    search_filter_dropdown: str = ".filter-dropdown, [data-testid='filter-dropdown']"
    search_suggestion: str = ".search-suggestion, [data-testid='search-suggestion']"

    # ========== 发布页选择器 ==========
    publish_button: str = ".publish-btn, .create-note, [data-testid='publish-button']"
    publish_page: str = ".publish-page, .editor-page, [data-testid='publish-page']"
    publish_title_input: str = ".title-input, [data-testid='title-input']"
    publish_content_area: str = ".content-area, [contenteditable='true'], [data-testid='content-area']"
    publish_image_upload: str = ".image-upload, .upload-btn, [data-testid='image-upload']"
    publish_video_upload: str = ".video-upload, .video-btn, [data-testid='video-upload']"
    publish_submit: str = ".publish-submit, .submit-btn, [data-testid='publish-submit']"
    publish_cancel: str = ".publish-cancel, .cancel-btn, [data-testid='publish-cancel']"
    publish_image_preview: str = ".image-preview, .preview-image, [data-testid='image-preview']"
    publish_video_preview: str = ".video-preview, .preview-video, [data-testid='video-preview']"

    # ========== 弹窗选择器 ==========
    modal_overlay: str = ".modal-overlay, .overlay, .el-overlay"
    modal_container: str = ".modal-container, .el-dialog, [data-testid='modal']"
    confirm_button: str = ".confirm-btn, .el-button--primary, [data-testid='confirm']"
    cancel_button: str = ".cancel-btn, .el-button--default, [data-testid='cancel']"
    close_button: str = ".close-btn, .el-dialog__close, [data-testid='close']"
    dialog_title: str = ".dialog-title, .el-dialog__title, [data-testid='dialog-title']"
    dialog_body: str = ".dialog-body, .el-dialog__body, [data-testid='dialog-body']"


class XHSExtraSelectors(BaseModel):
    """
    小红书备用选择器

    当主选择器失败时使用的备用选择器列表。
    """

    # 通用备用选择器
    generic_container: List[str] = Field(
        default_factory=lambda: [
            "[data-testid]",
            ".el-container",
            ".main-container"
        ],
        description="通用容器备用选择器"
    )

    # 首页备用选择器
    feed_card_alternatives: List[str] = Field(
        default_factory=lambda: [
            "[data-testid='feed-card']",
            ".feed-item",
            ".note-item",
            ".card-item",
            "[class*='feed']",
            "[class*='note']"
        ],
        description="笔记卡片备用选择器"
    )

    # 详情页备用选择器
    detail_container_alternatives: List[str] = Field(
        default_factory=lambda: [
            "[data-testid='note-detail']",
            ".note-detail-page",
            ".detail-container",
            "[class*='detail']",
            "[class*='note']"
        ],
        description="详情页备用选择器"
    )

    # 登录备用选择器
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


class XHSSelectorSet(BaseModel):
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
            fallback_key: 备用选择器 key

        Returns:
            Optional[str]: 选择器值
        """
        # 获取主选择器
        primary_selector = self.get_selector(primary)
        if primary_selector:
            return primary_selector

        # 获取备用选择器
        fallback_selectors = self.extra.fallback_chains.get(fallback_key, [])
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

    def to_dict(self) -> Dict[str, any]:
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
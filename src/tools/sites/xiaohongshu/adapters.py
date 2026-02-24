"""
小红书网站适配器

实现 Site 抽象基类，提供小红书特定的 RPA 操作。
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List
from pydantic import Field

if TYPE_CHECKING:
    from src.tools.base import ExecutionContext

from src.tools.base import ExecutionContext
from src.core.result import Result, Error

from src.tools.business.site_base import Site, SiteConfig, SiteSelectorSet, PageInfo
from src.tools.business.errors import BusinessException, BusinessErrorCode

# 导入新框架的工具（替代旧的 src.tools.xhs）
from .utils import (
    ReadPageDataTool,
    InjectScriptTool,
    VideoDownloadTool,
    VideoChunkTransferTool,
    VideoUploadInterceptTool,
    UploadFileTool,
    SetFilesTool,
    get_video_store,
)


class XHSSiteConfig(SiteConfig):
    """
    小红书网站配置

    Attributes:
        site_name: 网站标识
        base_url: 基础 URL
        timeout: 默认超时
        retry_count: 重试次数
        need_login: 是否需要登录
    """
    site_name: str = "xiaohongshu"
    base_url: str = "https://www.xiaohongshu.com"
    timeout: int = 30000
    retry_count: int = 3
    need_login: bool = True


class XHSSelectors(SiteSelectorSet):
    """
    小红书选择器集合

    继承通用选择器集合，添加小红书特定的 CSS 选择器。
    """

    # ========== 登录相关选择器 ==========
    login_button: str = ".login-btn, [data-testid='login-btn']"
    logout_button: str = ".logout-btn, [data-testid='logout-btn']"
    user_avatar: str = ".user-avatar, [data-testid='user-avatar']"
    username_display: str = ".user-name, [data-testid='username']"
    qrcode_login_tab: str = ".tab-qrcode, [data-testid='qrcode-tab']"
    qrcode_image: str = ".qrcode-image, [data-testid='qrcode']"
    login_status_indicator: str = "[data-testid='login-status']"

    # ========== 弹窗/对话框选择器 ==========
    modal_overlay: str = ".modal-overlay, .overlay, .el-overlay"
    confirm_button: str = ".confirm-btn, [data-testid='confirm'], .el-button--primary"
    cancel_button: str = ".cancel-btn, [data-testid='cancel'], .el-button--default"
    close_button: str = ".close-btn, [data-testid='close'], .el-dialog__close"
    cookie_accept_button: str = ".cookie-accept, [data-testid='cookie-accept'], .cookie-agree"

    # ========== 首页/Feeds 选择器 ==========
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

    # ========== 笔记详情页选择器 ==========
    detail_container: str = ".note-detail, .detail-page, [data-testid='note-detail']"
    detail_title: str = ".note-title, [data-testid='note-title']"
    detail_content: str = ".note-content, [data-testid='note-content']"
    detail_images: List[str] = [".note-image", ".detail-image", "[data-testid='detail-image']"]
    detail_likes: str = ".detail-likes, .likes-count, [data-testid='detail-likes']"
    detail_collects: str = ".detail-collects, .collects-count, [data-testid='detail-collects']"
    detail_comments: str = ".detail-comments, .comments-section, [data-testid='detail-comments']"
    detail_comment_input: str = ".comment-input, [contenteditable='true'], [data-testid='comment-input']"
    detail_comment_submit: str = ".comment-submit, .send-comment, [data-testid='comment-submit']"
    detail_author: str = ".detail-author, [data-testid='detail-author']"
    detail_author_info: str = ".author-info, [data-testid='author-info']"

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

    # ========== 搜索页选择器 ==========
    search_container: str = ".search-page, .search-result, [data-testid='search-page']"
    search_input: str = ".search-input, [contenteditable='true'], [data-testid='search-input']"
    search_button: str = ".search-btn, .search-icon, [data-testid='search-btn']"
    search_result: str = ".search-result-item, [data-testid='search-result']"
    search_no_result: str = ".no-result, .empty-result, [data-testid='no-result']"
    search_filter: str = ".search-filter, .filter-item, [data-testid='search-filter']"
    search_filter_dropdown: str = ".filter-dropdown, [data-testid='filter-dropdown']"

    # ========== 发布相关选择器 ==========
    publish_button: str = ".publish-btn, .create-note, [data-testid='publish-button']"
    publish_page: str = ".publish-page, .editor-page, [data-testid='publish-page']"
    publish_title_input: str = ".title-input, [data-testid='title-input']"
    publish_content_area: str = ".content-area, [contenteditable='true'], [data-testid='content-area']"
    publish_image_upload: str = ".image-upload, .upload-btn, [data-testid='image-upload']"
    publish_video_upload: str = ".video-upload, .video-btn, [data-testid='video-upload']"
    publish_submit: str = ".publish-submit, .submit-btn, [data-testid='publish-submit']"
    publish_cancel: str = ".publish-cancel, .cancel-btn, [data-testid='publish-cancel']"

    # ========== 加载/等待相关选择器 ==========
    loading_spinner: str = ".loading, .spinner, [data-testid='loading']"
    infinite_scroll: str = ".infinite-scroll, .scroll-loading, [data-testid='infinite-scroll']"
    load_more: str = ".load-more, .load-btn, [data-testid='load-more']"


class XiaohongshuSite(Site):
    """
    小红书网站 RPA 操作适配器

    实现 Site 抽象基类的所有方法，提供小红书特定的 RPA 操作。

    Attributes:
        config: 小红书配置
        selectors: 小红书选择器集合
    """

    config: XHSSiteConfig = XHSSiteConfig()
    selectors: XHSSelectors = XHSSelectors()

    # ========== 页面类型定义 ==========

    PAGE_TYPES = [
        "home",      # 首页
        "login",     # 登录页
        "explore",   # 发现页
        "feed",      # 笔记详情页
        "profile",   # 用户主页
        "search",    # 搜索页
        "publish",   # 发布页
        "message",   # 消息页
        "notification",  # 通知页
    ]

    # ========== 抽象方法实现 ==========

    async def navigate(
        self,
        page: str,
        page_id: Optional[str] = None,
        context: 'ExecutionContext' = None
    ) -> Result[bool]:
        """
        导航到小红书页面

        Args:
            page: 页面类型
                - home: 首页
                - login: 登录页
                - profile: 用户主页 (需要 page_id)
                - feed: 笔记详情页 (需要 page_id)
                - search: 搜索页 (需要 page_id)
            page_id: 页面 ID (用户 ID、笔记 ID、搜索关键词等)
            context: 执行上下文

        Returns:
            Result[bool]: 导航是否成功
        """
        from src.tools.browser.navigate import NavigateTool
        from src.tools.browser.wait import WaitTool

        # 构建 URL
        url_map = {
            "home": f"{self.base_url}/",
            "login": f"{self.base_url}/",
            "explore": f"{self.base_url}/explore",
            "feed": f"{self.base_url}/explore/{page_id}" if page_id else None,
            "profile": f"{self.base_url}/user/profile/{page_id}" if page_id else None,
            "search": f"{self.base_url}/search/{page_id}" if page_id else None,
        }

        url = url_map.get(page)
        if not url:
            return Result.fail(
                error=Error.unknown(
                    message=f"不支持的页面类型: {page}",
                    details={
                        "supported_types": self.PAGE_TYPES,
                        "received_type": page
                    }
                )
            )

        try:
            # 执行导航
            nav_tool = NavigateTool()
            nav_result = await nav_tool.execute(
                params=nav_tool._get_params_type()(
                    url=url,
                    timeout=self.config.timeout
                ),
                context=context or self._create_default_context()
            )

            if not nav_result.success:
                return Result.fail(
                    error=Error.unknown(
                        message=f"导航失败: {nav_result.error}",
                        details={"url": url}
                    )
                )

            # 等待页面加载完成
            await self._wait_page_ready(context)

            # 处理 Cookie 弹窗
            await self.accept_cookies(context)

            # 验证页面
            page_info = await self.get_page_info(context)
            if not page_info.success:
                return Result.fail(
                    error=Error.unknown(
                        message="无法获取页面信息",
                        details={"error": page_info.error}
                    )
                )

            return Result.ok(True)

        except Exception as e:
            return self.error_from_exception(e)

    async def check_login_status(
        self,
        context: 'ExecutionContext' = None,
        silent: bool = False
    ) -> Result[Dict[str, Any]]:
        """
        检查小红书登录状态

        Args:
            context: 执行上下文
            silent: 是否静默模式（减少日志输出，适合轮询场景）

        Returns:
            Result[Dict]: 包含以下字段的字典
                - is_logged_in: bool, 是否已登录
                - username: Optional[str], 用户名
                - user_id: Optional[str], 用户 ID
                - avatar: Optional[str], 头像 URL
        """
        import logging
        logger = logging.getLogger("xiaohongshu")
        if not silent:
            logger.info("[check_login_status] === 开始检查登录状态 ===")

        import logging
        logger = logging.getLogger("xiaohongshu")
        from src.tools.business.errors import BusinessException

        try:
            ctx = context or self._create_default_context()

            # 获取 client - 从 context 中获取
            client = getattr(ctx, 'client', None)

            # 如果没有 client，返回错误（需要通过上层传递 client）
            if not client:
                if not silent:
                    logger.warning("[check_login_status] 上下文无 client，无法访问浏览器")
                return Result.fail(
                    "无法获取浏览器连接，请确保通过 API 调用",
                    details={"reason": "no_client_in_context"}
                )

            # 辅助函数：通过 client 执行浏览器工具读取页面数据
            async def read_page_data(path: str):
                try:
                    result = await client.execute_tool("read_page_data", {
                        "path": path
                    }, timeout=10)
                    if result.get("success"):
                        return result.get("data")
                    return None
                except Exception as e:
                    logger.debug(f"[check_login_status] read_page_data 失败: {e}")
                    return None

            # ========================================
            # 方式1: 尝试读取全局变量中的用户信息
            # ========================================
            data_sources = [
                # 常见全局变量
                "__INITIAL_STATE__.user.userInfo",
                "__NUXT__.data.0.userInfo",
                "window.__USER_INFO__",
                "__INITIAL_STATE__",
                "__NUXT__",
                # 小红书可能使用的其他全局变量
                "window.__XHS_USER_INFO__",
                "window.__xhs_user_info__",
                "window.__XhsLogin__",
                "window.xhs",
                "window.XHS",
            ]

            # 先尝试获取页面 URL 和 Title（用于调试）
            url_data = await read_page_data("location.href")
            title_data = await read_page_data("document.title")
            # 调试信息 - 仅在非静默模式打印
            if not silent:
                logger.info(f"[check_login_status] 页面 URL: {url_data if url_data else 'N/A'}")
                logger.info(f"[check_login_status] 页面 Title: {title_data if title_data else 'N/A'}")
                # 尝试列出所有 window 上的变量
                window_keys_data = await read_page_data("Object.keys(window).filter(k => k.includes('xhs') || k.includes('XHS') || k.includes('INITIAL') || k.includes('NUXT') || k.includes('USER'))")
                logger.info(f"[check_login_status] window 相关变量: {window_keys_data if window_keys_data else 'N/A'}")

            # 尝试读取 cookie 中的登录信息
            cookie_data = await read_page_data("document.cookie")

            user_info = None
            last_error = None
            for source in data_sources:
                try:
                    data = await read_page_data(source)
                    if data:
                        user_info = data
                        # 如果是 __INITIAL_STATE__ 或 __NUXT__，尝试提取嵌套的 userInfo
                        if source in ("__INITIAL_STATE__", "__NUXT__") and isinstance(user_info, dict):
                            if "userInfo" in user_info:
                                user_info = user_info["userInfo"]
                            elif "user" in user_info and isinstance(user_info.get("user"), dict):
                                user_info = user_info["user"]
                        break
                except Exception as e:
                    last_error = e
                    continue

            # 记录调试信息
            if not silent:
                logger.info(f"[check_login_status] === 全局变量检查 ===")
                logger.info(f"[check_login_status] 已检查的数据源: {data_sources}")
                logger.info(f"[check_login_status] 最终获取的 user_info: {user_info}")
                if last_error:
                    logger.info(f"[check_login_status] 最后错误: {last_error}")

            # 检查用户信息
            if user_info and isinstance(user_info, dict):
                is_logged_in = (
                    user_info.get("isLogin", False) or
                    user_info.get("isLoggedIn", False) or
                    user_info.get("login") or
                    user_info.get("loggedIn") or
                    user_info.get("uid") or
                    user_info.get("userId")
                )
                if not silent:
                    logger.info(f"[check_login_status] 全局变量登录检测: is_logged_in={is_logged_in}")
                    logger.info(f"[check_login_status] user_info keys: {list(user_info.keys()) if isinstance(user_info, dict) else 'N/A'}")

                if is_logged_in:
                    username = (
                        user_info.get("nickname") or
                        user_info.get("userName") or
                        user_info.get("name")
                    )
                    logger.info(f"[check_login_status] ✓ 全局变量检测到已登录: username={username}")
                    return Result.ok({
                        "is_logged_in": True,
                        "username": username,
                        "user_id": user_info.get("userId") or user_info.get("uid"),
                        "avatar": user_info.get("avatar") or user_info.get("userImage"),
                    })
                else:
                    if not silent:
                        logger.info(f"[check_login_status] ✗ 全局变量检测未登录，继续检查...")

            # ========================================
            # 方式2: 通过 DOM 元素检查登录状态（参考原 Go 实现）
            # ========================================
            # 检查用户相关的 DOM 元素（已登录用户会显示用户名/头像等）
            login_selectors = [
                ".main-container .user .link-wrapper .channel",  # 原 Go 代码使用
                ".user-info",  # 用户信息区域
                ".user-avatar",  # 用户头像
                "[data-testid='user-avatar']",
                ".login-user-info",  # 登录用户信息
                ".header-user",  # 头部用户区域
                ".user-name",  # 用户名
                ".channel-user",  # 频道用户
            ]

            if not silent:
                logger.info(f"[check_login_status] === DOM 元素检查 ===")
                logger.info(f"[check_login_status] 检查登录元素选择器: {login_selectors}")

            dom_login_check = None
            for selector in login_selectors:
                try:
                    data = await read_page_data(f"document.querySelector('{selector}')")
                    if not silent:
                        logger.info(f"[check_login_status] 选择器 '{selector}': data={data}")
                    if data:
                        dom_login_check = True
                        if not silent:
                            logger.info(f"[check_login_status] ✓ DOM 选择器 {selector} 找到元素")
                        break
                except Exception as e:
                    if not silent:
                        logger.info(f"[check_login_status] 选择器 '{selector}' 异常: {e}")
                    continue

            if dom_login_check:
                # 尝试从 DOM 获取用户名
                username = None
                for name_selector in [".user-name", "[data-testid='username']", ".nickname"]:
                    try:
                        data = await read_page_data(f"document.querySelector('{name_selector}')?.textContent")
                        if data:
                            username = data
                            break
                    except Exception:
                        continue

                logger.debug(f"[check_login_status] DOM 检测到已登录: username={username}")
                return Result.ok({
                    "is_logged_in": True,
                    "username": username,
                    "user_id": None,
                    "avatar": None,
                })

            # ========================================
            # 方式3: 检查登录相关元素是否存在（未登录状态）
            # ========================================
            logout_selectors = [
                ".login-btn",
                "[data-testid='login-btn']",
                ".guest-user",  # 访客用户
            ]

            if not silent:
                logger.info(f"[check_login_status] === 未登录元素检查 ===")
                logger.info(f"[check_login_status] 检查未登录元素选择器: {logout_selectors}")

            for selector in logout_selectors:
                try:
                    data = await read_page_data(f"document.querySelector('{selector}')")
                    if not silent:
                        logger.info(f"[check_login_status] 未登录选择器 '{selector}': data={data}")
                    if data:
                        if not silent:
                            logger.info(f"[check_login_status] ✓ 找到未登录元素: {selector}")
                        return Result.ok({
                            "is_logged_in": False,
                            "username": None,
                            "user_id": None,
                            "avatar": None,
                        })
                except Exception as e:
                    if not silent:
                        logger.info(f"[check_login_status] 未登录选择器 '{selector}' 异常: {e}")
                    continue

            # ========================================
            # 方式4: 检查页面 URL
            # ========================================
            page_info = await self.get_page_info(context)
            if not silent:
                logger.info(f"[check_login_status] === 页面 URL 检查 ===")

            if page_info.success:
                url = page_info.data.url if page_info.data else ""
                title = page_info.data.title if page_info.data else ""
                if not silent:
                    logger.info(f"[check_login_status] 页面 URL: {url}")
                    logger.info(f"[check_login_status] 页面 Title: {title}")

                # 如果 URL 包含 login 路径，认为未登录
                if url and "/login" in url:
                    if not silent:
                        logger.info(f"[check_login_status] URL 包含 /login，返回未登录")
                    return Result.ok({
                        "is_logged_in": False,
                        "username": None,
                        "user_id": None,
                        "avatar": None,
                    })
            else:
                if not silent:
                    logger.info(f"[check_login_status] 获取页面信息失败: {page_info.error}")

            # ========================================
            # 最终结果
            # ========================================
            if not silent:
                logger.warning("[check_login_status] ✗ 所有检查方式都无法确定登录状态，默认返回未登录")
                logger.info(f"[check_login_status] === 检查结束 ===")
            return Result.ok({
                "is_logged_in": False,
                "username": None,
                "user_id": None,
                "avatar": None,
            })

        except BusinessException:
            raise
        except Exception as e:
            logger.error(f"[check_login_status] 异常: {e}", exc_info=True)
            return Result.fail(
                error=Error.from_exception(e)
            )

    async def extract_data(
        self,
        data_type: str,
        context: 'ExecutionContext' = None,
        max_items: int = 20
    ) -> Result[Any]:
        """
        提取小红书页面数据

        Args:
            data_type: 数据类型
                - feed_list: 笔记列表
                - feed_detail: 笔记详情
                - user_profile: 用户主页
                - comments: 评论列表
                - search_results: 搜索结果
            context: 执行上下文
            max_items: 最大提取数量

        Returns:
            Result[Any]: 提取的数据
        """
        from src.tools.business.errors import BusinessException

        try:
            extractors = {
                "feed_list": self._extract_feed_list,
                "feed_detail": self._extract_feed_detail,
                "user_profile": self._extract_user_profile,
                "comments": self._extract_comments,
                "search_results": self._extract_search_results,
            }

            extractor = extractors.get(data_type)
            if not extractor:
                return Result.fail(
                    error=Error.unknown(
                        message=f"不支持的数据类型: {data_type}",
                        details={
                            "supported_types": list(extractors.keys()),
                            "received_type": data_type
                        }
                    )
                )

            return await extractor(context, max_items)

        except BusinessException:
            raise
        except Exception as e:
            return Result.fail(
                error=Error.from_exception(e)
            )

    async def wait_for_element(
        self,
        selector: str,
        timeout: int = 10000,
        context: 'ExecutionContext' = None
    ) -> Result[bool]:
        """
        等待元素出现在页面中

        Args:
            selector: CSS 选择器
            timeout: 超时时间（毫秒）
            context: 执行上下文

        Returns:
            Result[bool]: 元素是否出现
        """
        from src.tools.browser.wait import WaitTool

        try:
            wait_tool = WaitTool()
            ctx = context or self._create_default_context()

            result = await wait_tool.execute(
                params=wait_tool._get_params_type()(
                    selector=selector,
                    timeout=timeout
                ),
                context=ctx
            )

            return result

        except Exception as e:
            from src.tools.business.errors import BusinessException
            return Result.fail(
                error=Error.from_exception(e)
            )

    # ========== 可选覆盖方法实现 ==========

    async def _wait_page_ready(self, context: 'ExecutionContext' = None):
        """
        等待页面加载完成

        Args:
            context: 执行上下文
        """
        from src.tools.browser.wait import WaitTool

        try:
            # 等待页面主体加载
            await self.wait_for_element(
                "body",
                timeout=10000,
                context=context
            )

            # 等待主要内容区域
            await self.wait_for_element(
                ".main-content, [data-testid='main-content']",
                timeout=15000,
                context=context
            )

        except Exception:
            # 忽略超时错误，继续执行
            pass

    def _create_default_context(self) -> 'ExecutionContext':
        """创建默认执行上下文"""
        return ExecutionContext(
            timeout=self.config.timeout,
            retry_count=self.config.retry_count
        )

    # ========== 数据提取辅助方法 ==========

    async def _extract_feed_list(
        self,
        context: 'ExecutionContext',
        max_items: int
    ) -> Result[Dict[str, Any]]:
        """提取笔记列表数据"""
        tool = ReadPageDataTool()
        ctx = context or self._create_default_context()

        try:
            # 读取页面中的笔记列表数据
            sources = [
                "__INITIAL_STATE__.explore.feeds",
                "__NUXT__.data.0.feeds",
                "window.__FEEDS__",
            ]

            feeds_data = None
            for source in sources:
                try:
                    result = await tool.execute(
                        params=tool._get_params_type()(path=source),
                        context=ctx
                    )
                    if result.success and result.data:
                        feeds_data = result.data
                        break
                except Exception:
                    continue

            if not feeds_data:
                return Result.fail(
                    error=Error.unknown(
                        message="无法提取笔记列表数据",
                        details={"suggestion": "页面结构可能已更新，请检查选择器"}
                    )
                )

            # 解析笔记数据
            items = []
            for feed in feeds_data[:max_items]:
                if isinstance(feed, dict):
                    items.append({
                        "note_id": feed.get("noteId") or feed.get("id"),
                        "xsec_token": feed.get("xsec_token") or feed.get("xsecToken"),
                        "title": feed.get("title"),
                        "cover_image": feed.get("cover") or feed.get("image"),
                        "author": {
                            "user_id": feed.get("user", {}).get("userId"),
                            "nickname": feed.get("user", {}).get("nickname"),
                            "avatar": feed.get("user", {}).get("avatar"),
                        },
                        "likes": feed.get("likedCount", 0),
                        "comments": feed.get("commentCount", 0),
                        "collects": feed.get("collectCount", 0),
                    })

            return Result.ok({
                "items": items,
                "count": len(items),
                "has_more": len(feeds_data) > max_items,
            })

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def _extract_feed_detail(
        self,
        context: 'ExecutionContext',
        max_items: int
    ) -> Result[Dict[str, Any]]:
        """提取笔记详情数据"""
        tool = ReadPageDataTool()
        ctx = context or self._create_default_context()

        try:
            # 读取笔记详情数据
            sources = [
                "__INITIAL_STATE__.note.detailNote",
                "__NUXT__.data.0.note",
                "window.__NOTE_DETAIL__",
            ]

            detail_data = None
            for source in sources:
                try:
                    result = await tool.execute(
                        params=tool._get_params_type()(path=source),
                        context=ctx
                    )
                    if result.success and result.data:
                        detail_data = result.data
                        break
                except Exception:
                    continue

            if not detail_data:
                return Result.fail(
                    error=Error.unknown(message="无法提取笔记详情数据")
                )

            # 解析详情数据
            result_data = {
                "note_id": detail_data.get("noteId"),
                "title": detail_data.get("title"),
                "content": detail_data.get("desc") or detail_data.get("content"),
                "images": detail_data.get("imageList", []) or detail_data.get("images", []),
                "video": detail_data.get("video"),
                "author": {
                    "user_id": detail_data.get("user", {}).get("userId"),
                    "nickname": detail_data.get("user", {}).get("nickname"),
                    "avatar": detail_data.get("user", {}).get("avatar"),
                    "description": detail_data.get("user", {}).get("description"),
                },
                "interactions": {
                    "likes": detail_data.get("likedCount", 0),
                    "collects": detail_data.get("collectCount", 0),
                    "comments": detail_data.get("commentCount", 0),
                    "shares": detail_data.get("shareCount", 0),
                },
                "comments": [],  # 评论列表需要单独提取
            }

            return Result.ok(result_data)

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def _extract_user_profile(
        self,
        context: 'ExecutionContext',
        max_items: int
    ) -> Result[Dict[str, Any]]:
        """提取用户主页数据"""
        tool = ReadPageDataTool()
        ctx = context or self._create_default_context()

        try:
            # 读取用户数据
            sources = [
                "__INITIAL_STATE__.user.profile",
                "__NUXT__.data.0.user",
                "window.__USER_PROFILE__",
            ]

            user_data = None
            for source in sources:
                try:
                    result = await tool.execute(
                        params=tool._get_params_type()(path=source),
                        context=ctx
                    )
                    if result.success and result.data:
                        user_data = result.data
                        break
                except Exception:
                    continue

            if not user_data:
                return Result.fail(
                    error=Error.unknown(message="无法提取用户主页数据")
                )

            # 解析用户数据
            result_data = {
                "user_id": user_data.get("userId"),
                "nickname": user_data.get("nickname"),
                "avatar": user_data.get("avatar"),
                "description": user_data.get("description"),
                "followers": user_data.get("followerCount", 0),
                "following": user_data.get("followingCount", 0),
                "likes": user_data.get("likesCount", 0),
                "notes_count": user_data.get("notesCount", 0),
                "notes": [],  # 笔记列表需要单独提取
            }

            return Result.ok(result_data)

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def _extract_comments(
        self,
        context: 'ExecutionContext',
        max_items: int
    ) -> Result[Dict[str, Any]]:
        """提取评论列表数据"""
        tool = ReadPageDataTool()
        ctx = context or self._create_default_context()

        try:
            # 读取评论数据
            sources = [
                "__INITIAL_STATE__.note.comments",
                "__NUXT__.data.0.comments",
                "window.__COMMENTS__",
            ]

            comments_data = None
            for source in sources:
                try:
                    result = await tool.execute(
                        params=tool._get_params_type()(path=source),
                        context=ctx
                    )
                    if result.success and result.data:
                        comments_data = result.data
                        break
                except Exception:
                    continue

            if not comments_data:
                return Result.fail(
                    error=Error.unknown(message="无法提取评论数据")
                )

            # 解析评论数据
            items = []
            for comment in comments_data[:max_items]:
                if isinstance(comment, dict):
                    items.append({
                        "comment_id": comment.get("commentId"),
                        "content": comment.get("content"),
                        "user": {
                            "user_id": comment.get("user", {}).get("userId"),
                            "nickname": comment.get("user", {}).get("nickname"),
                            "avatar": comment.get("user", {}).get("avatar"),
                        },
                        "likes": comment.get("likeCount", 0),
                        "replies": comment.get("replies", []),
                        "create_time": comment.get("createTime"),
                    })

            return Result.ok({
                "items": items,
                "count": len(items),
                "has_more": len(comments_data) > max_items,
            })

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def _extract_search_results(
        self,
        context: 'ExecutionContext',
        max_items: int
    ) -> Result[Dict[str, Any]]:
        """提取搜索结果数据"""
        tool = ReadPageDataTool()
        ctx = context or self._create_default_context()

        try:
            # 读取搜索结果数据
            sources = [
                "__INITIAL_STATE__.search.feeds",
                "__NUXT__.data.0.searchResults",
                "window.__SEARCH_RESULTS__",
            ]

            results_data = None
            for source in sources:
                try:
                    result = await tool.execute(
                        params=tool._get_params_type()(path=source),
                        context=ctx
                    )
                    if result.success and result.data:
                        results_data = result.data
                        break
                except Exception:
                    continue

            if not results_data:
                return Result.fail(
                    error=Error.unknown(message="无法提取搜索结果数据")
                )

            # 解析搜索结果
            items = []
            for item in results_data[:max_items]:
                if isinstance(item, dict):
                    items.append({
                        "note_id": item.get("noteId"),
                        "title": item.get("title"),
                        "cover": item.get("cover"),
                        "author": {
                            "user_id": item.get("user", {}).get("userId"),
                            "nickname": item.get("user", {}).get("nickname"),
                        },
                        "likes": item.get("likedCount", 0),
                        "comments": item.get("commentCount", 0),
                    })

            return Result.ok({
                "items": items,
                "count": len(items),
                "query": "",  # 搜索关键词需要从上下文获取
            })

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    # ========== 页面信息获取 ==========

    async def get_page_info(self, context: 'ExecutionContext' = None) -> Result[PageInfo]:
        """
        获取当前页面信息

        Args:
            context: 执行上下文

        Returns:
            Result[PageInfo]: 页面信息
        """
        try:
            tool = ReadPageDataTool()
            ctx = context or self._create_default_context()

            # 获取 URL
            url_result = await tool.execute(
                params=tool._get_params_type()(path="location.href"),
                context=ctx
            )

            # 获取标题
            title_result = await tool.execute(
                params=tool._get_params_type()(path="document.title"),
                context=ctx
            )

            # 检查登录状态
            login_status = await self.check_login_status(ctx, silent=True)

            url = url_result.data if url_result.success else None
            title = title_result.data if title_result.success else None

            # 判断是否登录页
            is_login_page = bool(
                (url and "/login" in url) or
                (title and "登录" in title)
            )

            return Result.ok(PageInfo(
                url=url,
                title=title,
                is_login_page=is_login_page,
                is_logged_in=login_status.data.get("is_logged_in", False) if login_status.success else False
            ))

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    # ========== Cookie 处理 ==========

    async def clear_cookies(self, context: 'ExecutionContext' = None) -> Result[bool]:
        """
        清除小红书相关 Cookie

        Args:
            context: 执行上下文

        Returns:
            Result[bool]: 是否清除成功
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            result = await control_tool.execute(
                params=control_tool._get_params_type()(
                    action="clear_cookies",
                    params={"domains": [self.base_url]}
                ),
                context=context or self._create_default_context()
            )

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def delete_cookies(
        self,
        context: 'ExecutionContext' = None,
        delete_all: bool = True,
        cookie_names: list = None
    ) -> Result[Dict[str, Any]]:
        """
        删除小红书 Cookie

        Args:
            context: 执行上下文
            delete_all: 是否删除所有 Cookie
            cookie_names: 要删除的特定 Cookie 名称列表

        Returns:
            Result[Dict[str, Any]]: 删除结果，包含 deleted_count 和 deleted_names
        """
        from src.tools.browser.control import ControlTool
        from src.tools.browser.navigate import NavigateTool
        import logging

        logger = logging.getLogger("xhs_delete_cookies")

        try:
            control_tool = ControlTool()

            # 获取 context 和 tab_id
            ctx = context or self._create_default_context()
            tab_id = ctx.tab_id if ctx else None

            # 如果没有 tab_id，先导航到小红书创建新标签页
            created_new_tab = False
            if tab_id is None:
                logger.info("[adapter.delete_cookies] 未提供 tab_id，先导航到小红书创建标签页")
                nav_tool = NavigateTool()
                nav_result = await nav_tool.execute(
                    params=nav_tool._get_params_type()(
                        url="https://www.xiaohongshu.com",
                        new_tab=True,
                        timeout=30000
                    ),
                    context=ctx
                )
                if not nav_result.success or not nav_result.data:
                    logger.error(f"[adapter.delete_cookies] 导航失败: {nav_result.error}")
                    return Result.fail(f"导航到小红书失败: {nav_result.error}")

                # 从导航结果获取 tab_id
                nav_data = nav_result.data if isinstance(nav_result.data, dict) else {}
                tab_id = nav_data.get("tabId")
                created_new_tab = True
                logger.info(f"[adapter.delete_cookies] 新建标签页 tab_id={tab_id}")

                # 更新 context 中的 tab_id
                ctx.tab_id = tab_id

            # 构建删除参数
            params_dict = {
                "action": "delete_cookies",
                "params": {}
            }

            if delete_all:
                params_dict["params"]["delete_all"] = True
            elif cookie_names:
                params_dict["params"]["cookie_names"] = cookie_names

            logger.info(
                f"[adapter.delete_cookies] 开始删除 Cookie - "
                f"tab_id={tab_id}, delete_all={delete_all}, cookie_names={cookie_names}"
            )

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=ctx
            )

            logger.info(
                f"[adapter.delete_cookies] ControlTool 执行结果 - "
                f"success={result.success}, error={result.error}, data={result.data}"
            )

            # 如果是新建的标签页，关闭它
            if created_new_tab and tab_id:
                logger.info(f"[adapter.delete_cookies] 关闭新建的标签页 tab_id={tab_id}")
                # 可以选择是否关闭，这里选择不关闭以便用户查看

            if result.success:
                # 返回格式化的结果
                return Result.ok({
                    "deleted_count": len(cookie_names) if cookie_names else 0,
                    "deleted_names": cookie_names or [],
                    "success": True
                })

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def get_login_qrcode(
        self,
        context: 'ExecutionContext' = None
    ) -> Result[Dict[str, Any]]:
        """
        获取小红书登录二维码

        注意：实际业务逻辑已移至 tools/login/get_login_qrcode.py 的 _execute_core 中
        此方法保留为 Site 抽象基类的接口实现

        Args:
            context: 执行上下文

        Returns:
            Result[Dict[str, Any]]: 二维码结果
        """
        # 业务逻辑已在 get_login_qrcode.py 的 _execute_core 中实现
        return Result.ok({
            "qrcode_url": None,
            "qrcode_data": None,
            "message": "业务逻辑在 tools/login/get_login_qrcode.py 中实现"
        })

    # ========== 发布相关方法 ==========

    async def publish_content(
        self,
        context: 'ExecutionContext' = None,
        title: str = None,
        content: str = None,
        images: list = None,
        topic_tags: list = None,
        at_users: list = None,
        open_location: str = None
    ) -> Result[Dict[str, Any]]:
        """
        发布小红书图文笔记

        Args:
            context: 执行上下文
            title: 笔记标题
            content: 笔记正文
            images: 图片路径列表
            topic_tags: 话题标签列表
            at_users: @用户列表
            open_location: 位置信息

        Returns:
            Result[Dict[str, Any]]: 发布结果，包含 note_id 和 url
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 导航到发布页面
            await self.navigate("publish", context=context)

            # 构建发布参数
            params_dict = {
                "action": "publish_content",
                "title": title,
                "content": content,
                "images": images or [],
            }

            if topic_tags:
                params_dict["topic_tags"] = topic_tags
            if at_users:
                params_dict["at_users"] = at_users
            if open_location:
                params_dict["open_location"] = open_location

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            if result.success:
                data = result.data if isinstance(result.data, dict) else {}
                return Result.ok({
                    "note_id": data.get("note_id"),
                    "url": data.get("url"),
                })

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def publish_video(
        self,
        context: 'ExecutionContext' = None,
        title: str = None,
        content: str = None,
        video_path: str = None,
        cover_image: str = None,
        topic_tags: list = None,
        at_users: list = None,
        open_location: str = None
    ) -> Result[Dict[str, Any]]:
        """
        发布小红书视频笔记

        Args:
            context: 执行上下文
            title: 笔记标题
            content: 笔记正文
            video_path: 视频文件路径
            cover_image: 封面图片路径
            topic_tags: 话题标签列表
            at_users: @用户列表
            open_location: 位置信息

        Returns:
            Result[Dict[str, Any]]: 发布结果，包含 note_id 和 url
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 导航到发布页面
            await self.navigate("publish", context=context)

            # 构建发布参数
            params_dict = {
                "action": "publish_video",
                "title": title,
                "content": content,
                "video_path": video_path,
            }

            if cover_image:
                params_dict["cover_image"] = cover_image
            if topic_tags:
                params_dict["topic_tags"] = topic_tags
            if at_users:
                params_dict["at_users"] = at_users
            if open_location:
                params_dict["open_location"] = open_location

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            if result.success:
                data = result.data if isinstance(result.data, dict) else {}
                return Result.ok({
                    "note_id": data.get("note_id"),
                    "url": data.get("url"),
                })

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def schedule_publish(
        self,
        context: 'ExecutionContext' = None,
        title: str = None,
        content: str = None,
        images: list = None,
        video_path: str = None,
        schedule_time: str = None,
        timezone: str = "Asia/Shanghai",
        topic_tags: list = None,
        at_users: list = None,
        open_location: str = None
    ) -> Result[Dict[str, Any]]:
        """
        定时发布小红书笔记

        Args:
            context: 执行上下文
            title: 笔记标题
            content: 笔记正文
            images: 图片路径列表
            video_path: 视频文件路径
            schedule_time: 定时发布时间
            timezone: 时区
            topic_tags: 话题标签列表
            at_users: @用户列表
            open_location: 位置信息

        Returns:
            Result[Dict[str, Any]]: 定时任务结果，包含 task_id
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 导航到发布页面
            await self.navigate("publish", context=context)

            # 构建定时发布参数
            params_dict = {
                "action": "schedule_publish",
                "title": title,
                "content": content,
                "schedule_time": schedule_time,
                "timezone": timezone,
            }

            if images:
                params_dict["images"] = images
            if video_path:
                params_dict["video_path"] = video_path
            if topic_tags:
                params_dict["topic_tags"] = topic_tags
            if at_users:
                params_dict["at_users"] = at_users
            if open_location:
                params_dict["open_location"] = open_location

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            if result.success:
                data = result.data if isinstance(result.data, dict) else {}
                return Result.ok({
                    "task_id": data.get("task_id"),
                    "scheduled_time": schedule_time,
                })

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def check_publish_status(
        self,
        context: 'ExecutionContext' = None,
        note_id: str = None
    ) -> Result[Dict[str, Any]]:
        """
        检查小红书笔记发布状态

        Args:
            context: 执行上下文
            note_id: 笔记 ID

        Returns:
            Result[Dict[str, Any]]: 状态结果，包含 status、views、likes 等
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 构建查询参数
            params_dict = {
                "action": "check_publish_status",
            }

            if note_id:
                params_dict["note_id"] = note_id

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            if result.success:
                data = result.data if isinstance(result.data, dict) else {}
                return Result.ok({
                    "note_id": note_id,
                    "status": data.get("status", "unknown"),
                    "publish_time": data.get("publish_time"),
                    "views": data.get("views", 0),
                    "likes": data.get("likes", 0),
                })

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    # ========== 搜索相关方法 ==========

    async def search(
        self,
        context: 'ExecutionContext' = None,
        keyword: str = None,
        search_type: str = "notes",
        max_items: int = 20
    ) -> Result[Dict[str, Any]]:
        """
        搜索小红书内容

        Args:
            context: 执行上下文
            keyword: 搜索关键词
            search_type: 搜索类型（notes/users/tags）
            max_items: 最大返回数量

        Returns:
            Result[Dict[str, Any]]: 搜索结果列表
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 导航到搜索页面
            await self.navigate("search", page_id=keyword, context=context)

            # 构建搜索参数
            params_dict = {
                "action": "search",
                "keyword": keyword,
                "search_type": search_type,
                "max_items": max_items,
            }

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            if result.success:
                data = result.data if isinstance(result.data, dict) else {}
                return Result.ok({
                    "items": data.get("items", []),
                    "keyword": keyword,
                    "search_type": search_type,
                    "total_count": data.get("total_count", 0),
                })

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    # ========== 互动相关方法 ==========

    async def like_feed(
        self,
        context: 'ExecutionContext' = None,
        note_id: str = None,
        action: str = "like"
    ) -> Result[Dict[str, Any]]:
        """
        点赞或取消点赞笔记

        Args:
            context: 执行上下文
            note_id: 笔记 ID
            action: 操作类型（like/unlike）

        Returns:
            Result[Dict[str, Any]]: 操作结果
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 构建参数
            params_dict = {
                "action": "like_feed",
                "note_id": note_id,
                "action_type": action,
            }

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def favorite_feed(
        self,
        context: 'ExecutionContext' = None,
        note_id: str = None,
        action: str = "favorite",
        folder_name: str = None
    ) -> Result[Dict[str, Any]]:
        """
        收藏或取消收藏笔记

        Args:
            context: 执行上下文
            note_id: 笔记 ID
            action: 操作类型（favorite/unfavorite）
            folder_name: 收藏文件夹名称

        Returns:
            Result[Dict[str, Any]]: 操作结果
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 构建参数
            params_dict = {
                "action": "favorite_feed",
                "note_id": note_id,
                "action_type": action,
            }

            if folder_name:
                params_dict["folder_name"] = folder_name

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def post_comment(
        self,
        context: 'ExecutionContext' = None,
        note_id: str = None,
        content: str = None,
        at_users: list = None
    ) -> Result[Dict[str, Any]]:
        """
        发表评论

        Args:
            context: 执行上下文
            note_id: 笔记 ID
            content: 评论内容
            at_users: @用户列表

        Returns:
            Result[Dict[str, Any]]: 评论结果
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 构建参数
            params_dict = {
                "action": "post_comment",
                "note_id": note_id,
                "content": content,
            }

            if at_users:
                params_dict["at_users"] = at_users

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            if result.success:
                data = result.data if isinstance(result.data, dict) else {}
                return Result.ok({
                    "comment_id": data.get("comment_id"),
                    "content": content,
                })

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))

    async def reply_comment(
        self,
        context: 'ExecutionContext' = None,
        comment_id: str = None,
        content: str = None
    ) -> Result[Dict[str, Any]]:
        """
        回复评论

        Args:
            context: 执行上下文
            comment_id: 评论 ID
            content: 回复内容

        Returns:
            Result[Dict[str, Any]]: 回复结果
        """
        from src.tools.browser.control import ControlTool

        try:
            control_tool = ControlTool()

            # 构建参数
            params_dict = {
                "action": "reply_comment",
                "comment_id": comment_id,
                "content": content,
            }

            result = await control_tool.execute(
                params=control_tool._get_params_type()(**params_dict),
                context=context or self._create_default_context()
            )

            if result.success:
                data = result.data if isinstance(result.data, dict) else {}
                return Result.ok({
                    "reply_id": data.get("reply_id"),
                    "comment_id": comment_id,
                    "content": content,
                })

            return result

        except Exception as e:
            return Result.fail(Error.from_exception(e))


__all__ = [
    "XHSSiteConfig",
    "XHSSelectors",
    "XiaohongshuSite",
]
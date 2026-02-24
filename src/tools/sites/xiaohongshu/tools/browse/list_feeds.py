"""
小红书浏览笔记列表工具

实现 xhs_list_feeds 工具，获取小红书笔记列表。
"""

import logging
import asyncio
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.errors import BusinessException
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSListFeedsParams
from .result import XHSListFeedsResult, XHSFeedItem

# 创建日志记录器
logger = logging.getLogger("xhs_list_feeds")


class ListFeedsTool(BusinessTool[XiaohongshuSite, XHSListFeedsParams]):
    """
    获取小红书笔记列表

    支持获取首页、发现页、关注页的笔记列表。

    Usage:
        tool = ListFeedsTool()
        result = await tool.execute(
            params=XHSListFeedsParams(
                page_type="home",
                max_items=20
            ),
            context=context
        )

        if result.success:
            for item in result.data.items:
                print(f"{item.title}: {item.likes} 点赞")
    """

    name = "xhs_list_feeds"
    description = "获取小红书笔记列表，支持首页、发现页、关注页"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "browse"
    site_type = XiaohongshuSite
    required_login = False

    @log_operation("xhs_list_feeds")
    async def _execute_core(
        self,
        params: XHSListFeedsParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑 - 参考登录工具的多选择器遍历模式

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）
            site: 网站适配器实例

        Returns:
            XHSListFeedsResult: 获取结果
        """
        logger.info("开始获取小红书笔记列表")
        logger.debug(f"参数: tab_id={params.tab_id}, page_type={params.page_type}, max_items={params.max_items}")

        # 从 context 获取 client
        client = getattr(context, 'client', None)
        logger.debug(f"从 context 获取 client: {client is not None}")

        if not client:
            # 如果 context 没有 client，调用 site 的方法
            return await self._extract_via_site(params, context, site)

        # ========== tab_id 管理 ==========
        # 优先级：参数 > context > 获取活动标签页 > 创建新标签页
        tab_id = params.tab_id
        logger.debug(f"初始 tab_id: {tab_id}")

        if not tab_id:
            # 从 context 获取 tab_id
            tab_id = context.tab_id
            logger.debug(f"从 context 获取 tab_id: {tab_id}")

        if not tab_id:
            # 获取当前活动标签页
            logger.info("尝试获取当前活动标签页...")
            tab_result = await client.execute_tool("browser_control", {
                "action": "get_active_tab"
            }, timeout=10000)
            logger.debug(f"get_active_tab 结果: {tab_result}")

            if tab_result.get("success") and tab_result.get("data"):
                tab_id = tab_result.get("data", {}).get("tabId")
                logger.info(f"获取到活动标签页: tabId={tab_id}")
            else:
                logger.warning(f"获取活动标签页失败: {tab_result.get('error')}")

        # 如果仍然没有 tab_id，创建新标签页导航到小红书
        if not tab_id:
            logger.info("尝试创建新标签页导航到小红书...")
            # 根据 page_type 确定目标 URL
            url = self._get_page_url(params.page_type)
            nav_result = await client.execute_tool("chrome_navigate", {
                "url": url,
                "newTab": True
            }, timeout=15000)
            logger.debug(f"chrome_navigate 结果: {nav_result}")

            if nav_result.get("success") and nav_result.get("data"):
                tab_id = nav_result.get("data", {}).get("tabId")
                logger.info(f"创建新标签页成功: tabId={tab_id}")
            else:
                logger.warning(f"创建新标签页失败: {nav_result.get('error')}")

        # 如果还是没有 tab_id，抛出错误
        if not tab_id:
            logger.error("无法获取或创建标签页，浏览器可能未打开")
            return XHSListFeedsResult(
                success=False,
                message="无法获取或创建标签页，请确保浏览器已打开"
            )

        logger.debug(f"最终使用的 tab_id: {tab_id}")

        # ========== 等待页面加载 ==========
        await asyncio.sleep(3)

        # ========== DOM 元素检测 - 使用多选择器遍历模式 ==========
        # 检查笔记列表容器是否存在
        feed_container_selectors = [
            ".feeds-container",           # 笔记列表容器
            ".note-feed-list",          # 笔记Feed列表
            ".explore-feed-list",       # 发现页列表
            "[class*='feed-list']",     # 含 feed-list 的元素
            "[class*='note-list']",     # 含 note-list 的元素
            ".main-container .content", # 主内容区
        ]

        logger.info(f"开始检测笔记列表容器，共 {len(feed_container_selectors)} 个选择器")

        container_found = False
        for selector in feed_container_selectors:
            check_code = "document.querySelector('" + selector + "') !== null"
            result = await client.execute_tool("inject_script", {
                "code": check_code,
                "tabId": tab_id
            }, timeout=1500)
            logger.debug(f"选择器 {selector} 结果: {result.get('data')}")

            if result.get("success") and result.get("data") is True:
                logger.info(f"检测到笔记列表容器: {selector}")
                container_found = True
                break

        if not container_found:
            logger.warning("未检测到笔记列表容器，尝试从页面数据提取")

        # ========== 检测并关闭登录弹窗 ==========
        await self._close_login_popup(client, tab_id)

        # ========== 从页面提取数据 ==========
        # 方法1: 尝试从 JavaScript 全局变量获取数据
        sources = [
            "__INITIAL_STATE__.explore.feeds",
            "__INITIAL_STATE__.note.feeds",
            "__NUXT__.data.0.feeds",
            "window.__FEEDS__",
            "__INITIAL_STATE__.home.feeds",
            "__INITIAL_STATE__.discover.feeds",
        ]

        feeds_data = None
        for source in sources:
            logger.debug(f"尝试从 {source} 获取数据...")
            try:
                result = await client.execute_tool("read_page_data", {
                    "path": source,
                    "tabId": tab_id
                }, timeout=15000)

                if result.get("success") and result.get("data"):
                    data = result.get("data")
                    # 检查是否有有效数据
                    if isinstance(data, list) and len(data) > 0:
                        feeds_data = data
                        logger.info(f"从 {source} 获取到 {len(feeds_data)} 条笔记数据")
                        break
                    elif isinstance(data, dict) and (data.get("items") or data.get("data")):
                        feeds_data = data.get("items") or data.get("data")
                        if feeds_data:
                            logger.info(f"从 {source} 获取到 {len(feeds_data)} 条笔记数据")
                            break
            except Exception as e:
                logger.debug(f"从 {source} 获取失败: {str(e)}")
                continue

        # 方法2: 如果全局变量没有数据，尝试通过 DOM 选择器提取
        if not feeds_data or (isinstance(feeds_data, list) and len(feeds_data) == 0):
            logger.info("尝试通过 DOM 选择器提取笔记数据...")
            feeds_data = await self._extract_feeds_via_dom(client, tab_id, params.max_items)

        # ========== 解析数据 ==========
        if not feeds_data or (isinstance(feeds_data, list) and len(feeds_data) == 0):
            logger.warning("未能获取到笔记数据，尝试滚动页面加载更多")
            # 可以在这里添加滚动页面逻辑
            return XHSListFeedsResult(
                success=True,
                items=[],
                has_more=False,
                total_count=0,
                message="未找到笔记，请确保页面已加载或尝试滚动"
            )

        # 转换为 FeedItem 列表
        feed_items = []
        for feed in feeds_data[:params.max_items]:
            if isinstance(feed, dict):
                # 兼容两种数据格式：
                # 1. 全局变量格式: {noteId, title, cover, user{userId, nickname}, likedCount, ...}
                # 2. DOM 提取格式: {title, cover_image, author, likes, note_id, url}

                # 判断是否为 DOM 提取格式
                is_dom_format = "cover_image" in feed or "author" in feed and isinstance(feed.get("author"), str)

                if is_dom_format:
                    # DOM 提取格式
                    author_val = feed.get("author", "")
                    author_info = {
                        "user_id": feed.get("user_id", ""),
                        "nickname": author_val if isinstance(author_val, str) else "",
                        "avatar": feed.get("avatar", "")
                    }
                else:
                    # 全局变量格式
                    author_info = {
                        "user_id": feed.get("user", {}).get("userId") or feed.get("user", {}).get("id"),
                        "nickname": feed.get("user", {}).get("nickname") or feed.get("user", {}).get("name"),
                        "avatar": feed.get("user", {}).get("avatar") or feed.get("user", {}).get("userImage"),
                    }

                feed_items.append(XHSFeedItem(
                    note_id=feed.get("noteId") or feed.get("id") or feed.get("note_id") or "",
                    title=feed.get("title") or feed.get("desc") or "",
                    cover_image=feed.get("cover") or feed.get("image") or feed.get("coverImage") or feed.get("cover_image", ""),
                    author=author_info,
                    likes=feed.get("likedCount", 0) or feed.get("likes", 0) or feed.get("likes", 0),
                    comments=feed.get("commentCount", 0) or feed.get("comments", 0),
                    collects=feed.get("collectCount", 0) or feed.get("collects", 0),
                    url=feed.get("noteUrl") or feed.get("url") or feed.get("note_url", "") or f"https://www.xiaohongshu.com/explore/{feed.get('noteId') or feed.get('id') or ''}",
                ))

        logger.info(f"成功提取 {len(feed_items)} 条笔记")
        return XHSListFeedsResult(
            success=True,
            items=feed_items,
            has_more=len(feeds_data) > params.max_items,
            total_count=len(feed_items),
            message=self._get_list_message(feed_items)
        )

    async def _extract_via_site(
        self,
        params: XHSListFeedsParams,
        context: ExecutionContext,
        site: Site
    ) -> XHSListFeedsResult:
        """通过 site 适配器提取数据（当 context 没有 client 时）"""
        logger.info("通过 site 适配器提取数据")

        extract_result = await site.extract_data(
            context=context,
            data_type="feed_list",
            max_items=params.max_items
        )

        if not extract_result.success:
            error_msg = extract_result.error.message if extract_result.error else "未知错误"
            logger.error(f"提取失败: {error_msg}")
            return XHSListFeedsResult(
                success=False,
                message=f"获取笔记列表失败: {error_msg}"
            )

        # 解析提取结果
        items_data = extract_result.data or []
        if isinstance(items_data, dict):
            items_data = items_data.get("items", [])

        # 转换为 FeedItem 列表
        feed_items = []
        for item_data in items_data:
            feed_items.append(XHSFeedItem(
                note_id=item_data.get("note_id"),
                title=item_data.get("title"),
                cover_image=item_data.get("cover_image"),
                author=item_data.get("author"),
                likes=item_data.get("likes", 0),
                comments=item_data.get("comments", 0),
                collects=item_data.get("collects", 0),
                url=item_data.get("url"),
            ))

        return XHSListFeedsResult(
            success=True,
            items=feed_items,
            has_more=len(feed_items) >= params.max_items,
            total_count=len(feed_items),
            message=self._get_list_message(feed_items)
        )

    async def _close_login_popup(self, client, tab_id: int) -> bool:
        """
        检测并关闭登录弹窗

        小红书在未登录时会弹出登录框，需要检测并关闭。

        Args:
            client: 浏览器客户端
            tab_id: 标签页 ID

        Returns:
            bool: 是否成功关闭弹窗
        """
        # 登录弹窗选择器列表（多选择器遍历）
        login_popup_selectors = [
            "#app > div:nth-child(1) > div > div.login-container",
            ".login-container",
            "[class*='login-popup']",
            "[class*='login-dialog']",
            ".red-login-popup",
        ]

        # 关闭按钮选择器列表
        close_button_selectors = [
            "#app > div:nth-child(1) > div > div.login-container > div.icon-btn-wrapper.close-button",
            ".login-container .close-button",
            ".login-container .icon-btn-wrapper.close-button",
            "[class*='login'] .close-btn",
            "[class*='login-popup'] .close",
        ]

        logger.info("开始检测登录弹窗...")

        # 步骤1: 检测登录弹窗是否存在
        popup_found = False
        for selector in login_popup_selectors:
            check_code = "document.querySelector('" + selector + "') !== null"
            result = await client.execute_tool("inject_script", {
                "code": check_code,
                "tabId": tab_id
            }, timeout=1500)
            logger.debug(f"检测登录弹窗选择器 {selector}: {result.get('data')}")

            if result.get("success") and result.get("data") is True:
                logger.info(f"检测到登录弹窗: {selector}")
                popup_found = True
                break

        if not popup_found:
            logger.debug("未检测到登录弹窗")
            return False

        # 步骤2: 点击关闭按钮
        logger.info("尝试关闭登录弹窗...")
        for selector in close_button_selectors:
            # 先检测关闭按钮是否存在
            check_code = "document.querySelector('" + selector + "') !== null"
            result = await client.execute_tool("inject_script", {
                "code": check_code,
                "tabId": tab_id
            }, timeout=1500)

            if result.get("success") and result.get("data") is True:
                # 点击关闭按钮
                click_code = "document.querySelector('" + selector + "').click()"
                click_result = await client.execute_tool("inject_script", {
                    "code": click_code,
                    "tabId": tab_id
                }, timeout=1500)
                logger.info(f"点击关闭按钮 {selector}: {click_result.get('success')}")

                # 等待弹窗关闭
                await asyncio.sleep(1)

                # 验证弹窗是否已关闭
                verify_code = "document.querySelector('" + login_popup_selectors[0] + "') === null"
                verify_result = await client.execute_tool("inject_script", {
                    "code": verify_code,
                    "tabId": tab_id
                }, timeout=1500)

                if verify_result.get("success") and verify_result.get("data") is True:
                    logger.info("登录弹窗已关闭")
                    return True
                else:
                    logger.warning("登录弹窗可能未完全关闭，继续尝试")
                    break

        logger.warning("未能关闭登录弹窗")
        return False

    def _get_page_url(self, page_type: str) -> str:
        """根据页面类型获取目标 URL"""
        url_map = {
            "home": "https://www.xiaohongshu.com/",
            "discover": "https://www.xiaohongshu.com/explore",
            "following": "https://www.xiaohongshu.com/following",
        }
        return url_map.get(page_type, "https://www.xiaohongshu.com/")

    async def _extract_feeds_via_dom(
        self,
        client,
        tab_id: int,
        max_items: int
    ) -> list:
        """
        通过 DOM 选择器提取笔记数据

        使用小红书页面的实际选择器提取笔记信息：
        - 标题: #exploreFeeds > section:nth-child(n) > div > div > a > span
        - 封面图: #exploreFeeds > section:nth-child(n) > div > a.cover.mask.ld > img (src)
        - 发布者: #exploreFeeds > section:nth-child(n) > div > div > div > a > span
        - 点赞数: #exploreFeeds > section:nth-child(n) > div > div > div > span > span.count

        Args:
            client: 浏览器客户端
            tab_id: 标签页 ID
            max_items: 最大获取数量

        Returns:
            list: 笔记数据列表
        """
        logger.info("开始通过 DOM 选择器提取笔记数据...")

        # 检查 #exploreFeeds 容器是否存在
        check_container = "document.querySelector('#exploreFeeds') !== null"
        container_result = await client.execute_tool("inject_script", {
            "code": check_container,
            "tabId": tab_id
        }, timeout=1500)

        if not (container_result.get("success") and container_result.get("data") is True):
            logger.warning("未找到 #exploreFeeds 容器")
            # 尝试备用容器
            alt_containers = ["#feeds", "#feed-list", ".explore-feeds", "[id*='feed']"]
            for alt_selector in alt_containers:
                check_alt = f"document.querySelector('{alt_selector}') !== null"
                alt_result = await client.execute_tool("inject_script", {
                    "code": check_alt,
                    "tabId": tab_id
                }, timeout=1500)
                if alt_result.get("success") and alt_result.get("data") is True:
                    logger.info(f"找到备用容器: {alt_selector}")
                    # 使用备用容器构建选择器
                    return await self._extract_feeds_from_container(
                        client, tab_id, alt_selector, max_items
                    )
            return []

        # 使用 #exploreFeeds 容器提取
        return await self._extract_feeds_from_container(
            client, tab_id, "#exploreFeeds", max_items
        )

    async def _extract_feeds_from_container(
        self,
        client,
        tab_id: int,
        container_selector: str,
        max_items: int
    ) -> list:
        """从指定容器中提取笔记数据"""
        import json

        # 使用 JavaScript 提取所有笔记数据
        # 注意：选择器需要根据实际页面结构调整
        js_code = f"""
        (function() {{
            const container = document.querySelector('{container_selector}');
            if (!container) return [];

            const sections = container.querySelectorAll('section');
            const items = [];

            for (let i = 0; i < Math.min(sections.length, {max_items}); i++) {{
                const section = sections[i];

                // 尝试多种可能的选择器组合
                let title = '';
                let titleEl = section.querySelector('div > div > a > span') ||
                              section.querySelector('div a span') ||
                              section.querySelector('[class*="title"] span') ||
                              section.querySelector('.note-title');
                if (titleEl) title = titleEl.textContent;

                // 封面图
                let coverImage = '';
                let coverEl = section.querySelector('div > a.cover img') ||
                              section.querySelector('a.cover img') ||
                              section.querySelector('[class*="cover"] img') ||
                              section.querySelector('.note-cover img');
                if (coverEl) coverImage = coverEl.src || coverEl.getAttribute('src');

                // 发布者
                let author = '';
                let authorEl = section.querySelector('div > div > div > a > span') ||
                               section.querySelector('div div a span') ||
                               section.querySelector('[class*="user"] a span') ||
                               section.querySelector('.author-name');
                if (authorEl) author = authorEl.textContent;

                // 点赞数
                let likes = 0;
                let likesEl = section.querySelector('div > div > div > span span.count') ||
                              section.querySelector('div div div span span.count') ||
                              section.querySelector('[class*="like"] span') ||
                              section.querySelector('.liked-count');
                if (likesEl) {{
                    const text = likesEl.textContent || '';
                    const num = text.replace(/[^0-9]/g, '');
                    likes = parseInt(num) || 0;
                }}

                if (title || coverImage) {{
                    items.push({{
                        title: title,
                        cover_image: coverImage,
                        author: author,
                        likes: likes,
                        note_id: '',
                        url: ''
                    }});
                }}
            }}

            return items;
        }})()
        """

        logger.debug(f"执行 DOM 提取脚本，容器: {container_selector}")
        result = await client.execute_tool("inject_script", {
            "code": js_code,
            "tabId": tab_id
        }, timeout=15000)

        if result.get("success") and result.get("data"):
            data = result.get("data")
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"通过 DOM 选择器获取到 {len(data)} 条笔记")
                return data

        logger.warning("DOM 选择器未能获取到笔记数据")
        return []

    def _get_list_message(self, items: list) -> str:
        """生成列表消息"""
        count = len(items)
        if count == 0:
            return "未找到笔记"
        elif count == 1:
            return "找到 1 篇笔记"
        else:
            return f"找到 {count} 篇笔记"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def list_feeds(
    page_type: str = "home",
    max_items: int = 20,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSListFeedsResult:
    """
    便捷的获取笔记列表函数

    Args:
        page_type: 页面类型
        max_items: 最大获取数量
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSListFeedsResult: 获取结果
    """
    tool = ListFeedsTool()
    params = XHSListFeedsParams(
        tab_id=tab_id,
        page_type=page_type,
        max_items=max_items
    )
    ctx = context or ExecutionContext()

    logger.info(f"执行工具: {tool.name}, params={params}, ctx: {ctx}")

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSListFeedsResult(
            success=False,
            message=f"获取失败: {result.error}"
        )


__all__ = [
    "ListFeedsTool",
    "list_feeds",
    "XHSListFeedsParams",
    "XHSListFeedsResult",
]
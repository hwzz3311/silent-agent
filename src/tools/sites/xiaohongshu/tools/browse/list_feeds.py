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
        logger.debug(f"参数: tab_id={params.tab_id}, page_type={params.page_type}, channel={params.channel}, max_items={params.max_items}")

        # ========== 频道切换 ==========
        if params.channel and params.channel != "recommend":
            await self._switch_channel(client, tab_id, params.channel)

        # 从 context 获取 client
        client = getattr(context, 'client', None)
        logger.debug(f"从 context 获取 client: {client is not None}")

        if not client:
            # 如果 context 没有 client，调用 site 的方法
            return await self._extract_via_site(params, context, site)

        # 小红书域名
        site_domain = "xiaohongshu.com"

        # ========== tab_id 管理 ==========
        # 优先级：参数 > context > site_tab_map > 获取活动标签页 > 创建新标签页
        tab_id = params.tab_id
        logger.debug(f"初始 tab_id: {tab_id}")

        if not tab_id:
            # 从 context 获取 tab_id
            tab_id = context.tab_id
            logger.debug(f"从 context 获取 tab_id: {tab_id}")

        if not tab_id and hasattr(client, 'get_site_tab'):
            # 从全局 site tab 映射获取
            tab_id = client.get_site_tab(site_domain)
            logger.debug(f"从 site_tab_map 获取 tab_id: {tab_id}")

            # 检测 tab 是否还可用
            if tab_id and not await self._is_tab_valid(client, tab_id):
                logger.warning(f"site_tab_map 中的 tab_id={tab_id} 已失效，将重新获取")
                if hasattr(client, 'clear_site_tab'):
                    client.clear_site_tab(site_domain)
                tab_id = None

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

        # 保存 tab_id 到全局映射
        if tab_id and hasattr(client, 'set_site_tab'):
            client.set_site_tab(site_domain, tab_id)
            logger.debug(f"保存 tab_id 到 site_tab_map: {site_domain} -> {tab_id}")

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

        # ========== 从页面提取数据（支持自动滚动加载更多） ==========
        # 策略：优先从全局变量获取（数据最完整），不足时通过 DOM 获取

        sources = [
            # 首页推荐相关
            "__INITIAL_STATE__.home.recommend",
            "__INITIAL_STATE__.home.feeds",
            "__INITIAL_STATE__.home.items",
            # 发现页相关
            "__INITIAL_STATE__.explore.feeds",
            "__INITIAL_STATE__.explore.items",
            "__INITIAL_STATE__.note.feeds",
            "__INITIAL_STATE__.note.items",
            # 通用
            "__NUXT__.data.0.feeds",
            "__NUXT__.data.0.items",
            "window.__FEEDS__",
            "window.__DATA__",
            "__INITIAL_STATE__.discover.feeds",
            # 小红书新版数据结构
            "window.__INITIAL_STATE__.home",
            "window.__INITIAL_STATE__.explore",
        ]

        feeds_data = None

        # 尝试从全局变量获取数据
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

        # 如果全局变量没有数据，通过 DOM 提取
        if not feeds_data or (isinstance(feeds_data, list) and len(feeds_data) == 0):
            logger.info("尝试通过 DOM 选择器提取笔记数据...")
            feeds_data = await self._extract_feeds_via_dom(client, tab_id, params.max_items)

        # 使用去重逻辑获取更多数据
        # 小红书 DOM 容器只维护 12 条数据，需要通过滚动替换
        seen_ids = set()  # 已获取的 note_id 集合
        if feeds_data:
            for item in feeds_data:
                note_id = item.get("noteId") or item.get("id") or item.get("note_id") or ""
                if note_id:
                    seen_ids.add(note_id)

        total_count = len(feeds_data) if feeds_data else 0
        max_scrolls = 10  # 最多滚动10次
        consecutive_no_new = 0  # 连续无新数据的次数

        while total_count < params.max_items and max_scrolls > 0:
            logger.info(f"当前获取 {total_count} 条，需要 {params.max_items} 条，滚动页面加载更多...")

            # 滚动到页面底部
            await self._scroll_to_bottom(client, tab_id)

            # 滚动后等待更长时间确保新内容完全加载（至少 4 秒）
            wait_seconds = 4.5
            logger.debug(f"等待 {wait_seconds} 秒让内容加载完成...")
            await asyncio.sleep(wait_seconds)

            # 滚动后重新获取数据
            new_feeds = None

            # 优先从全局变量获取
            for source in sources:
                try:
                    result = await client.execute_tool("read_page_data", {
                        "path": source,
                        "tabId": tab_id
                    }, timeout=15000)

                    if result.get("success") and result.get("data"):
                        data = result.get("data")
                        feed_list = None

                        if isinstance(data, list):
                            feed_list = data
                        elif isinstance(data, dict):
                            for field in ['items', 'data', 'feeds', 'list', 'notes', 'cardList']:
                                if field in data and isinstance(data[field], list):
                                    feed_list = data[field]
                                    break

                        if feed_list:
                            new_feeds = feed_list
                            logger.info(f"滚动后从 {source} 获取到 {len(new_feeds)} 条")
                            break
                except Exception:
                    continue

            # 如果全局变量没新数据通过 DOM 获取
            if not new_feeds:
                logger.info("滚动后通过 DOM 选择器重新提取...")
                new_feeds = await self._extract_feeds_via_dom(client, tab_id, params.max_items)

            # 去重处理 - 检查是否有新数据
            new_items = []
            if new_feeds:
                for item in new_feeds:
                    note_id = item.get("noteId") or item.get("id") or item.get("note_id") or ""
                    if note_id and note_id not in seen_ids:
                        new_items.append(item)
                        seen_ids.add(note_id)

            new_count = len(new_items)
            if new_count > 0:
                # 有新数据，追加到列表
                if feeds_data is None:
                    feeds_data = []
                feeds_data.extend(new_items)
                total_count = len(feeds_data)
                consecutive_no_new = 0
                logger.info(f"滚动后新增 {new_count} 条，共获取 {total_count} 条")
            else:
                # 无新数据
                consecutive_no_new += 1
                logger.info(f"滚动后无新数据（连续 {consecutive_no_new} 次）")

                # 连续 2 次无新数据说明已到底
                if consecutive_no_new >= 2:
                    logger.info("连续无新数据，认为已到底")
                    break

                # 如果 DOM 获取为空，尝试刷新页面
                if not new_feeds or (isinstance(new_feeds, list) and len(new_feeds) == 0):
                    logger.warning("DOM 获取为空，尝试刷新页面...")
                    refresh_result = await client.execute_tool("chrome_navigate", {
                        "url": "https://www.xiaohongshu.com/",
                        "newTab": False
                    }, timeout=10000)
                    if refresh_result.get("success"):
                        await asyncio.sleep(3)
                        max_scrolls -= 1
                        continue

            max_scrolls -= 1

        # ========== 检查是否获取到数据 ==========
        if not feeds_data or (isinstance(feeds_data, list) and len(feeds_data) == 0):
            logger.warning("未能获取到笔记数据")
            return XHSListFeedsResult(
                success=True,
                items=[],
                has_more=False,
                total_count=0,
                message="未找到笔记，请确保页面已加载"
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

    # 频道到 DOM ID 的映射
    CHANNEL_TO_DOM_ID = {
        "recommend": "homefeed_recommend",
        "fashion": "homefeed.fashion_v3",
        "food": "homefeed.food_v3",
        "cosmetics": "homefeed.cosmetics_v3",
        "movie_and_tv": "homefeed.movie_and_tv_v3",
        "career": "homefeed.career_v3",
        "love": "homefeed.love_v3",
        "household_product": "homefeed.household_product_v3",
        "gaming": "homefeed.gaming_v3",
        "travel": "homefeed.travel_v3",
        "fitness": "homefeed.fitness_v3",
    }

    async def _switch_channel(self, client, tab_id: int, channel: str) -> bool:
        """
        切换到指定频道

        Args:
            client: 浏览器客户端
            tab_id: 标签页 ID
            channel: 频道名称

        Returns:
            bool: 是否成功切换
        """
        dom_id = self.CHANNEL_TO_DOM_ID.get(channel)
        if not dom_id:
            logger.warning(f"未知的频道: {channel}")
            return False

        logger.info(f"尝试切换到频道: {channel} (dom_id: {dom_id})")

        # 构建选择器：#channel-container > div#{dom_id}
        # 注意：f-string 表达式中不能有反斜杠，所以先存储替换后的字符串
        escaped_dom_id = dom_id.replace('.', r'\.')
        selector = f"#channel-container > div#{escaped_dom_id}"

        # 检查频道 tab 是否存在
        check_code = f"document.querySelector('{selector}') !== null"
        result = await client.execute_tool("inject_script", {
            "code": check_code,
            "tabId": tab_id
        }, timeout=1500)

        if not (result.get("success") and result.get("data") is True):
            logger.warning(f"未找到频道 tab: {selector}")
            # 尝试备选选择器
            alt_selector = f"div#{escaped_dom_id}.channel"
            check_alt = f"document.querySelector('{alt_selector}') !== null"
            alt_result = await client.execute_tool("inject_script", {
                "code": check_alt,
                "tabId": tab_id
            }, timeout=1500)

            if alt_result.get("success") and alt_result.get("data") is True:
                selector = alt_selector
                logger.info(f"使用备选选择器: {selector}")
            else:
                logger.warning(f"频道 tab 不存在: {channel}")
                return False

        # 点击频道 tab
        click_code = f"""
        (function() {{
            const tab = document.querySelector('{selector}');
            if (tab) {{
                tab.click();
                return true;
            }}
            return false;
        }})()
        """
        click_result = await client.execute_tool("inject_script", {
            "code": click_code,
            "tabId": tab_id
        }, timeout=1500)

        if click_result.get("success") and click_result.get("data") is True:
            logger.info(f"成功点击频道: {channel}")
            # 等待内容加载
            await asyncio.sleep(2)
            return True
        else:
            logger.warning(f"点击频道失败: {channel}")
            return False

    async def _is_tab_valid(self, client, tab_id: int) -> bool:
        """
        检测标签页是否还可用

        通过尝试读取页面标题来判断 tab 是否有效

        Args:
            client: 浏览器客户端
            tab_id: 标签页 ID

        Returns:
            bool: tab 是否有效
        """
        try:
            # 尝试读取页面标题，如果 tab 已关闭会失败
            result = await client.execute_tool("read_page_data", {
                "path": "document.title",
                "tabId": tab_id
            }, timeout=5000)

            is_valid = result.get("success", False)
            logger.debug(f"检测 tab_id={tab_id} 是否有效: {is_valid}")
            return is_valid
        except Exception as e:
            logger.debug(f"检测 tab_id={tab_id} 有效性失败: {e}")
            return False

    async def _scroll_to_bottom(self, client, tab_id: int) -> bool:
        """
        滚动到页面底部

        使用分段滚动，每段滚动后等待确保触发懒加载

        Args:
            client: 浏览器客户端
            tab_id: 标签页 ID

        Returns:
            bool: 是否成功
        """
        import random
        logger.info("滚动到页面底部...")

        # 方案：使用简单的分步滚动，每次滚动后等待触发加载
        scroll_code = """
        (function() {
            const scrollHeight = document.body.scrollHeight;
            const windowHeight = window.innerHeight;
            const maxScroll = Math.max(0, scrollHeight - windowHeight);

            // 分4次滚动，确保每次都能触发懒加载
            const step = Math.ceil(maxScroll / 4);
            const positions = [step, step * 2, step * 3, maxScroll];

            positions.forEach((pos, index) => {
                setTimeout(() => {
                    window.scrollTo(0, pos);
                }, index * 300);
            });

            // 最后滚动到底部
            setTimeout(() => {
                window.scrollTo(0, document.body.scrollHeight);
            }, 1500);

            return true;
        })()
        """

        result = await client.execute_tool("inject_script", {
            "code": scroll_code,
            "tabId": tab_id
        }, timeout=5000)

        if result.get("success"):
            logger.debug("滚动到底部已触发")
            return True
        else:
            logger.warning("滚动到底部失败")
            return False

    async def _scroll_page(self, client, tab_id: int, scroll_count: int) -> bool:
        """
        滚动页面加载更多内容（隐蔽安全版本）

        使用更自然的滚动方式，避免被风控检测：
        - 每次滚动距离较小（约视口高度的 30-50%）
        - 带有随机延迟和随机滚动距离
        - 模拟人类滚动的缓动效果

        Args:
            client: 浏览器客户端
            tab_id: 标签页 ID
            scroll_count: 滚动次数

        Returns:
            bool: 是否成功
        """
        import random
        logger.info(f"开始隐蔽滚动页面 {scroll_count} 次...")

        for i in range(scroll_count):
            # 随机滚动距离（视口高度的 30-50%），模拟人类不规则滚动
            scroll_distance = f"window.innerHeight * {random.uniform(0.3, 0.5):.2f}"

            # 使用更自然的滚动方式：平滑滚动 + 随机延迟
            scroll_code = f"""
            (function() {{
                // 随机延时启动，模拟人类行为
                const delay = {random.randint(100, 500)};
                setTimeout(function() {{
                    // 使用 scrollTo 带平滑效果
                    const currentY = window.scrollY;
                    const targetY = currentY + {scroll_distance};
                    window.scrollTo({{
                        top: targetY,
                        behavior: 'smooth'
                    }});
                }}, delay);
                return true;
            }})()
            """

            result = await client.execute_tool("inject_script", {
                "code": scroll_code,
                "tabId": tab_id
            }, timeout=3000)

            if result.get("success"):
                logger.debug(f"第 {i+1} 次滚动已触发")

                # 随机等待时间（1.5-3秒），让滚动完成并加载新内容
                wait_time = random.uniform(1.5, 3.0)
                logger.debug(f"等待 {wait_time:.1f} 秒让内容加载...")
                await asyncio.sleep(wait_time)
            else:
                logger.warning(f"第 {i+1} 次滚动失败")

            # 每次滚动后额外随机等待，模拟人类阅读/思考时间
            extra_wait = random.uniform(0.5, 1.5)
            await asyncio.sleep(extra_wait)

        logger.info("页面滚动完成")
        return True

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
        # logger.info(f"js_code : {js_code}")
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
    channel: str = "recommend",
    max_items: int = 20,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSListFeedsResult:
    """
    便捷的获取笔记列表函数

    Args:
        page_type: 页面类型 (home/discover/following)
        channel: 频道类型 (recommend/fashion/food/cosmetics/movie_and_tv/career/love/household_product/gaming/travel/fitness)
        max_items: 最大获取数量（会自动滚动加载直到获取足够数量）
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSListFeedsResult: 获取结果
    """
    tool = ListFeedsTool()
    params = XHSListFeedsParams(
        tab_id=tab_id,
        page_type=page_type,
        channel=channel,
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
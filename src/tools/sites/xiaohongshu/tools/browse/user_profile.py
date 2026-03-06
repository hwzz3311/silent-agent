"""
小红书获取用户主页工具

实现 xhs_user_profile 工具，获取用户详细信息和笔记列表。
"""

import logging
import asyncio
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.domain import business_tool
from src.tools.domain.base import BusinessTool
from src.tools.domain.logging import log_operation
from src.tools.domain.site_base import Site
from src.tools.domain.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .types import XHSUserProfileParams, XHSUserProfileResult, XHSFeedItem

# 创建日志记录器
logger = logging.getLogger("xhs_user_profile")


@business_tool(name="xhs_user_profile", site_type=XiaohongshuSite, param_type=XHSUserProfileParams, operation_category="browse")
class UserProfileTool(BusinessTool):
    """
    获取小红书用户主页信息

    包括用户基本信息（昵称、头像、简介）和笔记列表。

    Usage:
        tool = UserProfileTool()
        result = await tool.execute(
            params=XHSUserProfileParams(user_id="user123"),
            context=context
        )

        if result.success:
            print(f"用户: {result.data.nickname}")
            print(f"粉丝: {result.data.followers}")
            print(f"笔记数: {result.data.notes_count}")
    """

    name = "xhs_user_profile"
    description = "获取小红书用户主页信息，包括用户信息和笔记列表"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "browse"
    site_type = XiaohongshuSite
    required_login = False

    # 使用基类的 tab 管理抽象
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/user/profile"

    @log_operation("xhs_user_profile")
    async def _execute_core(
        self,
        params: XHSUserProfileParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑 - 直接模式

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）
            site: 网站适配器实例

        Returns:
            XHSUserProfileResult: 用户主页结果
        """
        logger.info("开始获取小红书用户主页")

        # 使用 context.client（依赖注入）
        client = context.client
        if not client:
            return XHSUserProfileResult(
                success=False,
                user_id=params.user_id,
                message="无法获取浏览器客户端请确保通过 API 调用"
            )

        # ========== 使用 ensure_site_tab 获取标签页 ==========
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url=self.default_navigate_url,
            param_tab_id=params.tab_id
        )

        if not tab_id:
            logger.error("无法获取或创建标签页，浏览器可能未打开")
            return XHSUserProfileResult(
                success=False,
                user_id=params.user_id,
                message="无法获取或创建标签页请确保浏览器已打开"
            )

        logger.debug(f"最终使用的 tab_id: {tab_id}")

        # 等待页面加载
        await asyncio.sleep(2)

        # ========== 直接从页面提取用户数据 ==========
        user_data = await self._extract_user_profile_direct(client, tab_id)

        if not user_data:
            logger.warning("未能获取到用户数据")
            return XHSUserProfileResult(
                success=False,
                user_id=params.user_id,
                message="未能获取到用户数据请检查页面是否正确加载"
            )

        # 处理笔记列表
        notes = []
        if params.include_note and params.max_note > 0:
            # 从页面获取笔记列表
            notes_data = await self._extract_user_notes_direct(client, tab_id, params.max_note)
            for note_item in notes_data:
                notes.append(XHSFeedItem(
                    note_id=note_item.get("note_id"),
                    title=note_item.get("title"),
                    cover_image=note_item.get("cover_image"),
                    author=note_item.get("author"),
                    likes=note_item.get("likes", 0),
                    comments=note_item.get("comments", 0),
                    collects=note_item.get("collects", 0),
                    url=note_item.get("url"),
                ))

        return XHSUserProfileResult(
            success=True,
            user_id=params.user_id or user_data.get("user_id"),
            nickname=user_data.get("nickname"),
            avatar=user_data.get("avatar"),
            description=user_data.get("description"),
            followers=user_data.get("followers", 0),
            following=user_data.get("following", 0),
            likes=user_data.get("likes", 0),
            notes_count=user_data.get("notes_count", 0),
            notes=notes,
            message=self._get_profile_message(user_data)
        )

    async def _extract_user_profile_direct(self, client, tab_id: int) -> dict:
        """直接从页面提取用户主页数据"""
        source_list = [
            "__INITIAL_STATE__.user.profile",
            "__NUXT__.data.0.user",
            "window.__USER_PROFILE__",
        ]

        user_data = None
        for source in source_list:
            try:
                result = await client.execute_tool("read_page_data", {
                    "path": source,
                    "tabId": tab_id
                }, timeout=15000)

                if result.get("success") and result.get("data"):
                    user_data = result.get("data")
                    logger.debug(f"从 {source} 获取到用户数据")
                    break
            except Exception as e:
                logger.debug(f"从 {source} 获取失败: {e}")
                continue

        if not user_data:
            logger.warning("未能从全局变量获取用户数据")
            return None

        return {
            "user_id": user_data.get("userId"),
            "nickname": user_data.get("nickname"),
            "avatar": user_data.get("avatar"),
            "description": user_data.get("description"),
            "followers": user_data.get("followerCount", 0),
            "following": user_data.get("followingCount", 0),
            "likes": user_data.get("likesCount", 0),
            "notes_count": user_data.get("notesCount", 0),
        }

    async def _extract_user_notes_direct(self, client, tab_id: int, max_items: int) -> list:
        """直接从页面提取用户笔记列表"""
        source_list = [
            "__INITIAL_STATE__.user.notes",
            "__INITIAL_STATE__.user.profile.notes",
            "__NUXT__.data.0.notes",
            "window.__USER_NOTES__",
        ]

        notes_data = None
        for source in source_list:
            try:
                result = await client.execute_tool("read_page_data", {
                    "path": source,
                    "tabId": tab_id
                }, timeout=15000)

                if result.get("success") and result.get("data"):
                    data = result.get("data")
                    if isinstance(data, list) and len(data) > 0:
                        notes_data = data
                        logger.debug(f"从 {source} 获取到 {len(notes_data)} 条笔记")
                        break
                    elif isinstance(data, dict) and data.get("items"):
                        notes_data = data.get("items")
                        logger.debug(f"从 {source} 获取到 {len(notes_data)} 条笔记")
                        break
            except Exception as e:
                logger.debug(f"从 {source} 获取失败: {e}")
                continue

        if not notes_data:
            logger.warning("未能获取用户笔记列表")
            return []

        # 转换为标准格式
        items = []
        for note in notes_data[:max_items]:
            item_data = {
                "note_id": note.get("noteId") or note.get("id"),
                "title": note.get("title") or note.get("desc"),
                "cover_image": note.get("cover") or note.get("coverImage"),
                "author": note.get("user", {}).get("nickname") if isinstance(note.get("user"), dict) else "",
                "likes": note.get("likedCount", 0),
                "comments": note.get("commentCount", 0),
                "collects": note.get("collectCount", 0),
                "url": note.get("noteUrl") or f"https://www.xiaohongshu.com/explore/{note.get('noteId') or note.get('id')}",
            }
            items.append(item_data)

        return items

    def _get_profile_message(self, profile_data: dict) -> str:
        """生成用户主页消息"""
        nickname = profile_data.get("nickname")
        if nickname:
            return f"获取用户 {nickname} 的主页成功"
        return "获取用户主页成功"



# 便捷函数
async def user_profile(
    user_id: str = None,
    include_notes: bool = True,
    max_note: int = 20,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSUserProfileResult:
    """
    便捷的获取用户主页函数

    Args:
        user_id: 用户 ID（可选）
        include_notes: 是否包含笔记列表
        max_note: 最大获取笔记数量
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSUserProfileResult: 用户主页结果
    """
    tool = UserProfileTool()
    params = XHSUserProfileParams(
        tab_id=tab_id,
        user_id=user_id,
        include_notes=include_notes,
        max_note=max_note
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSUserProfileResult(
            success=False,
            user_id=user_id,
            message=f"获取失败: {result.error}"
        )


__all__ = [
    "UserProfileTool",
    "user_profile",
    "XHSUserProfileParams",
    "XHSUserProfileResult",
]
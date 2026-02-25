"""
小红书获取用户主页工具

实现 xhs_user_profile 工具，获取用户详细信息和笔记列表。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSUserProfileParams
from .result import XHSUserProfileResult, XHSFeedItem


class UserProfileTool(BusinessTool[XiaohongshuSite, XHSUserProfileParams]):
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

    @log_operation("xhs_user_profile")
    async def _execute_core(
        self,
        params: XHSUserProfileParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑

        Args:
            params: 工具参数
            context: 执行上下文
            site: 网站适配器实例

        Returns:
            XHSUserProfileResult: 用户主页结果
        """
        # 调用网站适配器的提取用户主页方法
        extract_result = await site.extract_data(
            context=context,
            data_type="user_profile",
            max_items=params.max_notes if params.include_notes else 0
        )

        if not extract_result.success:
            return XHSUserProfileResult(
                success=False,
                user_id=params.user_id,
                message=f"获取用户主页失败: {extract_result.error}"
            )

        # 解析用户主页结果
        profile_data = extract_result.data if isinstance(extract_result.data, dict) else {}

        # 处理笔记列表
        notes = []
        if params.include_notes:
            notes_data = profile_data.get("notes", [])
            for note_data in notes_data:
                notes.append(XHSFeedItem(
                    note_id=note_data.get("note_id"),
                    title=note_data.get("title"),
                    cover_image=note_data.get("cover_image"),
                    author=note_data.get("author"),
                    likes=note_data.get("likes", 0),
                    comments=note_data.get("comments", 0),
                    collects=note_data.get("collects", 0),
                    url=note_data.get("url"),
                ))

        return XHSUserProfileResult(
            success=True,
            user_id=params.user_id or profile_data.get("user_id"),
            nickname=profile_data.get("nickname"),
            avatar=profile_data.get("avatar"),
            description=profile_data.get("description"),
            followers=profile_data.get("followers", 0),
            following=profile_data.get("following", 0),
            likes=profile_data.get("likes", 0),
            notes_count=profile_data.get("notes_count", 0),
            notes=notes,
            message=self._get_profile_message(profile_data)
        )

    def _get_profile_message(self, profile_data: dict) -> str:
        """生成用户主页消息"""
        nickname = profile_data.get("nickname")
        if nickname:
            return f"获取用户 {nickname} 的主页成功"
        return "获取用户主页成功"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def user_profile(
    user_id: str = None,
    include_notes: bool = True,
    max_notes: int = 20,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSUserProfileResult:
    """
    便捷的获取用户主页函数

    Args:
        user_id: 用户 ID（可选）
        include_notes: 是否包含笔记列表
        max_notes: 最大获取笔记数量
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
        max_notes=max_notes
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
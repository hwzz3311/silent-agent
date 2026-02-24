"""
小红书浏览相关工具

包含笔记列表、搜索、详情、用户主页等工具。
"""

from .list_feeds import (
    ListFeedsTool,
    list_feeds,
    XHSListFeedsParams,
    XHSListFeedsResult,
)

from .search_feeds import (
    SearchFeedsTool,
    search_feeds,
    XHSSearchFeedsParams,
    XHSSearchFeedsResult,
)

from .get_feed_detail import (
    GetFeedDetailTool,
    get_feed_detail,
    XHSGetFeedDetailParams,
    XHSGetFeedDetailResult,
)

from .user_profile import (
    UserProfileTool,
    user_profile,
    XHSUserProfileParams,
    XHSUserProfileResult,
)


def register():
    """
    注册所有浏览相关工具

    Returns:
        int: 注册的工具数量
    """
    from src.tools.business.registry import BusinessToolRegistry

    count = 0

    if BusinessToolRegistry.register_by_class(ListFeedsTool):
        count += 1

    if BusinessToolRegistry.register_by_class(SearchFeedsTool):
        count += 1

    if BusinessToolRegistry.register_by_class(GetFeedDetailTool):
        count += 1

    if BusinessToolRegistry.register_by_class(UserProfileTool):
        count += 1

    return count


def get_tool_names() -> list:
    """获取所有浏览工具名称"""
    return [
        "xhs_list_feeds",
        "xhs_search_feeds",
        "xhs_get_feed_detail",
        "xhs_user_profile",
    ]


__all__ = [
    "register",
    "get_tool_names",
    "ListFeedsTool",
    "list_feeds",
    "SearchFeedsTool",
    "search_feeds",
    "GetFeedDetailTool",
    "get_feed_detail",
    "UserProfileTool",
    "user_profile",
]
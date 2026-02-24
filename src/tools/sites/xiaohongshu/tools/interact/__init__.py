"""
小红书互动相关工具

包含点赞、收藏、发表评论、回复评论等工具。
"""

from .like_feed import (
    LikeFeedTool,
    like_feed,
    XHSLikeFeedParams,
    XHSLikeFeedResult,
)

from .favorite_feed import (
    FavoriteFeedTool,
    favorite_feed,
    XHSFavoriteFeedParams,
    XHSFavoriteFeedResult,
)

from .post_comment import (
    PostCommentTool,
    post_comment,
    XHSPostCommentParams,
    XHSPostCommentResult,
)

from .reply_comment import (
    ReplyCommentTool,
    reply_comment,
    XHSReplyCommentParams,
    XHSReplyCommentResult,
)


def register():
    """
    注册所有互动相关工具

    Returns:
        int: 注册的工具数量
    """
    from src.tools.business.registry import BusinessToolRegistry

    count = 0

    if BusinessToolRegistry.register_by_class(LikeFeedTool):
        count += 1

    if BusinessToolRegistry.register_by_class(FavoriteFeedTool):
        count += 1

    if BusinessToolRegistry.register_by_class(PostCommentTool):
        count += 1

    if BusinessToolRegistry.register_by_class(ReplyCommentTool):
        count += 1

    return count


def get_tool_names() -> list:
    """获取所有互动工具名称"""
    return [
        "xhs_like_feed",
        "xhs_favorite_feed",
        "xhs_post_comment",
        "xhs_reply_comment",
    ]


__all__ = [
    "register",
    "get_tool_names",
    "LikeFeedTool",
    "like_feed",
    "FavoriteFeedTool",
    "favorite_feed",
    "PostCommentTool",
    "post_comment",
    "ReplyCommentTool",
    "reply_comment",
]
"""
小红书收藏工具

实现 xhs_favorite_feed 工具，收藏或取消收藏笔记。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSFavoriteFeedParams
from .result import XHSFavoriteFeedResult


class FavoriteFeedTool(BusinessTool[XiaohongshuSite, XHSFavoriteFeedParams]):
    """
    小红书收藏/取消收藏工具

    支持对笔记进行收藏或取消收藏操作。

    Usage:
        tool = FavoriteFeedTool()
        result = await tool.execute(
            params=XHSFavoriteFeedParams(
                note_id="abc123",
                action="favorite",
                folder_name="美妆"
            ),
            context=context
        )

        if result.success:
            print(f"收藏成功")
    """

    name = "xhs_favorite_feed"
    description = "收藏或取消收藏小红书笔记"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "interact"
    site_type = XiaohongshuSite
    required_login = True

    @log_operation("xhs_favorite_feed")
    async def _execute_core(
        self,
        params: XHSFavoriteFeedParams,
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
            XHSFavoriteFeedResult: 操作结果
        """
        # 调用网站适配器的收藏方法
        favorite_result = await site.favorite_feed(
            context,
            note_id=params.note_id,
            action=params.action,
            folder_name=params.folder_name
        )

        if not favorite_result.success:
            return XHSFavoriteFeedResult(
                success=False,
                note_id=params.note_id,
                action=params.action,
                message=f"收藏失败: {favorite_result.error}"
            )

        return XHSFavoriteFeedResult(
            success=True,
            note_id=params.note_id,
            action=params.action,
            folder_name=params.folder_name,
            message=self._get_favorite_message(params.action, params.folder_name)
        )

    def _get_favorite_message(self, action: str, folder_name: str = None) -> str:
        """生成收藏消息"""
        if action == "favorite":
            if folder_name:
                return f"已收藏到文件夹: {folder_name}"
            return "收藏成功"
        elif action == "unfavorite":
            return "取消收藏成功"
        else:
            return f"操作成功: {action}"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def favorite_feed(
    note_id: str,
    action: str = "favorite",
    folder_name: str = None,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSFavoriteFeedResult:
    """
    便捷的收藏函数

    Args:
        note_id: 笔记 ID
        action: 操作类型（favorite/unfavorite）
        folder_name: 收藏文件夹名称
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSFavoriteFeedResult: 操作结果
    """
    tool = FavoriteFeedTool()
    params = XHSFavoriteFeedParams(
        tab_id=tab_id,
        note_id=note_id,
        action=action,
        folder_name=folder_name
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSFavoriteFeedResult(
            success=False,
            note_id=note_id,
            action=action,
            message=f"操作失败: {result.error}"
        )


__all__ = [
    "FavoriteFeedTool",
    "favorite_feed",
    "XHSFavoriteFeedParams",
    "XHSFavoriteFeedResult",
]
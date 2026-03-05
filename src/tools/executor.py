"""
统一业务工具执行器

提供业务工具的统一定义和执行逻辑。
"""

import asyncio
import importlib
import inspect
from typing import Any, Dict, Optional
from src.core.result import Result


# 业务工具映射：API 工具名 -> (Python 模块路径, 函数名)
BUSINESS_TOOLS = {
    # 登录相关
    "xhs_check_login_status": (
        "src.tools.sites.xiaohongshu.tools.login",
        "check_login_status",
    ),
    "xhs_get_login_qrcode": (
        "src.tools.sites.xiaohongshu.tools.login",
        "get_login_qrcode",
    ),
    "xhs_wait_login": (
        "src.tools.sites.xiaohongshu.tools.login",
        "wait_login",
    ),
    "xhs_delete_cookies": (
        "src.tools.sites.xiaohongshu.tools.login",
        "delete_cookies",
    ),
    # 浏览相关
    "xhs_list_feeds": (
        "src.tools.sites.xiaohongshu.tools.browse",
        "list_feeds",
    ),
    "xhs_search_feeds": (
        "src.tools.sites.xiaohongshu.tools.browse",
        "search_feeds",
    ),
    "xhs_get_feed_detail": (
        "src.tools.sites.xiaohongshu.tools.browse",
        "get_feed_detail",
    ),
    "xhs_user_profile": (
        "src.tools.sites.xiaohongshu.tools.browse",
        "user_profile",
    ),
    # 互动相关
    "xhs_like_feed": (
        "src.tools.sites.xiaohongshu.tools.interact",
        "like_feed",
    ),
    "xhs_favorite_feed": (
        "src.tools.sites.xiaohongshu.tools.interact",
        "favorite_feed",
    ),
    "xhs_post_comment": (
        "src.tools.sites.xiaohongshu.tools.interact",
        "post_comment",
    ),
    "xhs_reply_comment": (
        "src.tools.sites.xiaohongshu.tools.interact",
        "reply_comment",
    ),
    # 发布相关
    "xhs_publish": (
        "src.tools.sites.xiaohongshu.publishers",
        "publish_note",
    ),
    "xhs_publish_content": (
        "src.tools.sites.xiaohongshu.publishers",
        "publish_note",
    ),
    "xhs_publish_video": (
        "src.tools.sites.xiaohongshu.publishers",
        "publish_video",
    ),
}


class BusinessToolExecutor:
    """统一业务工具执行器"""

    @staticmethod
    def execute(name: str, params: Dict[str, Any] = None, context: Any = None) -> Dict[str, Any]:
        """
        执行业务工具

        Args:
            name: 工具名称
            params: 工具参数
            context: 执行上下文

        Returns:
            执行结果字典
        """
        params = params or {}

        if name not in BUSINESS_TOOLS:
            raise ValueError(f"未知业务工具: {name}")

        # 统一获取 secret_key
        secret_key = getattr(context, 'secret_key', None) if context else None

        # 确保 context 有 secret_key 属性
        if context and not hasattr(context, 'secret_key'):
            context.secret_key = secret_key

        module_path, func_name = BUSINESS_TOOLS[name]

        # 动态导入模块和函数
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        # 调用函数
        try:
            sig = inspect.signature(func)
            if 'context' in sig.parameters:
                # 函数支持 context 参数
                result = func(**params, context=context)
            else:
                result = func(**params)

            # 如果结果是 coroutine，需要 await
            if asyncio.iscoroutine(result):
                result = asyncio.get_event_loop().run_until_complete(result)

            # 自动转换 Result 对象为标准格式
            return BusinessToolExecutor._convert_result(result)
        except Exception as e:
            raise ConnectionError(f"业务工具执行失败: {e}")

    @staticmethod
    def _convert_result(result: Any) -> Dict[str, Any]:
        """将 Result 对象转换为标准格式"""
        from pydantic import BaseModel

        if not isinstance(result, Result):
            if isinstance(result, BaseModel):
                return {
                    "success": result.success,
                    "data": result.model_dump(),
                    "error": None
                }
            return result

        return {
            "success": result.success,
            "data": result.data,
            "error": str(result.error) if result.error else None
        }


__all__ = ["BusinessToolExecutor", "BUSINESS_TOOLS"]

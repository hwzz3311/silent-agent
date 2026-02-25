"""
小红书登录检查工具

实现 xhs_check_login_status 工具，检查当前小红书登录状态。
"""

import logging
from typing import Any

from src.tools.base import ExecutionContext

from src.tools.business.base import BusinessTool
from src.tools.business.errors import BusinessException
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from src.client.client import SilentAgentClient
from .params import XHSCheckLoginStatusParams
from .result import XHSCheckLoginStatusResult

# 创建日志记录器
logger = logging.getLogger("xhs_check_login_status")


class CheckLoginStatusTool(BusinessTool[XiaohongshuSite, XHSCheckLoginStatusParams]):
    """
    检查小红书登录状态

    返回当前用户是否已登录，以及用户信息。

    Usage:
        tool = CheckLoginStatusTool()
        result = await tool.execute(
            params=XHSCheckLoginStatusParams(),
            context=context
        )

        if result.success:
            print(f"登录状态: {result.data.is_logged_in}")
            print(f"用户名: {result.data.username}")
    """

    name = "xhs_check_login_status"
    description = "检查小红书登录状态，返回用户名等信息"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "login"
    site_type = XiaohongshuSite
    required_login = False  # 此工具本身用于检查登录状态，不需要登录

    @log_operation("xhs_check_login_status")
    async def _execute_core(
        self,
        params: XHSCheckLoginStatusParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑 - 通过 context 获取的 client 执行浏览器操作

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）
            site: 网站适配器实例

        Returns:
            XHSCheckLoginStatusResult: 检查结果
        """
        logger.info("开始检查小红书登录状态")
        logger.debug(f"参数: tab_id={params.tab_id}")

        # 尝试从 context 获取 client
        client = getattr(context, 'client', None)
        logger.debug(f"从 context 获取 client: {client is not None}")

        if not client:
            # 如果 context 没有 client，调用 site 的方法（会在 API 层通过 relay 执行）
            login_result = await site.check_login_status(context)
            if not login_result.success:
                return XHSCheckLoginStatusResult(
                    success=False,
                    is_logged_in=False,
                    message=f"检查登录状态失败: {login_result.error}"
                )
            login_data = login_result.data if isinstance(login_result.data, dict) else {}
            return XHSCheckLoginStatusResult(
                success=True,
                is_logged_in=login_data.get("is_logged_in", False),
                username=login_data.get("username"),
                user_id=login_data.get("user_id"),
                avatar=login_data.get("avatar"),
                message=self._get_status_message(login_data)
            )

        # 使用 client 执行读取操作
        try:
            # 获取 tab_id，如果参数没有指定则获取当前活动标签页
            tab_id = params.tab_id
            logger.debug(f"初始 tab_id: {tab_id}")

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

            # 如果仍然没有 tab_id，尝试创建新标签页导航到小红书
            if not tab_id:
                logger.info("尝试创建新标签页导航到小红书...")
                nav_result = await client.execute_tool("chrome_navigate", {
                    "url": "https://www.xiaohongshu.com/",
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
                return XHSCheckLoginStatusResult(
                    success=False,
                    is_logged_in=False,
                    message="无法获取或创建标签页，请确保浏览器已打开"
                )

            logger.debug(f"最终使用的 tab_id: {tab_id}")

            tool_params = {"timeout": 10000, "tabId": tab_id}

            # 方法1: 使用 DOM 元素检测（与 xiaohongshu-mcp 相同的方式）
            # 使用 read_page_data 工具执行 JavaScript 检查元素
            login_element_selectors = [
                ".main-container .user .link-wrapper .channel",  # 小红书标准登录元素
                ".user-avatar",  # 用户头像
                ".header-user",  # 顶部用户区
                "[class*='user-info']",  # 用户信息
                ".red-login",  # 登录按钮
                ".unlogin-wrap",  # 未登录包裹
            ]

            logger.info(f"开始检测登录元素，共 {len(login_element_selectors)} 个选择器")

            for selector in login_element_selectors:
                # 使用 read_page_data 执行 JavaScript 检查元素是否存在
                logger.debug(f"检测选择器: {selector}")
                result = await client.execute_tool("read_page_data", {
                    "path": f"document.querySelector('{selector}') !== null",
                    **tool_params
                }, timeout=15)
                logger.debug(f"选择器 {selector} 结果: {result.get('data')}")

                if result.get("success") and result.get("data") is True:
                    logger.info(f"检测到登录元素: {selector}")
                    # 元素存在，认为已登录，尝试获取用户名
                    user_result = await client.execute_tool("read_page_data", {
                        "path": """
                        (function() {
                            var userInfo = null;
                            // 尝试从 __INITIAL_STATE__ 获取
                            try {
                                var state = window.__INITIAL_STATE__;
                                if (state && state.user && state.user.userInfo) {
                                    userInfo = state.user.userInfo;
                                }
                            } catch(e) {}
                            // 从 DOM 获取头像
                            if (!userInfo) {
                                var avatarEl = document.querySelector('.user-avatar img, [class*="avatar"] img, .header-user img');
                                if (avatarEl) {
                                    return { avatar: avatarEl.src };
                                }
                            }
                            return userInfo ? { username: userInfo.nickname || userInfo.userName || userInfo.name, userId: userInfo.userId || userInfo.uid, avatar: userInfo.avatar || userInfo.userImage } : { found: true };
                        })()
                        """,
                        **tool_params
                    }, timeout=15)
                    if user_result.get("success") and user_result.get("data"):
                        data = user_result.get("data")
                        if isinstance(data, dict) and data.get("username"):
                            return XHSCheckLoginStatusResult(
                                success=True,
                                is_logged_in=True,
                                username=data.get("username"),
                                user_id=data.get("userId"),
                                avatar=data.get("avatar"),
                                message=self._get_status_message({"is_logged_in": True, "username": data.get("username")})
                            )
                        # 元素存在但没获取到用户名也认为已登录
                        return XHSCheckLoginStatusResult(
                            success=True,
                            is_logged_in=True,
                            message="已登录"
                        )

            # 方法2: 后备方案 - 尝试从 JavaScript 变量获取
            # 注意：直接访问 ._rawValue 来获取 Vue ref 的实际值
            data_sources = [
                "__INITIAL_STATE__.user.userInfo._rawValue",
                "__INITIAL_STATE__.user.userInfo._value",
                "__NUXT__.data.0.userInfo._rawValue",
                "__NUXT__.data.0.userInfo._value",
                "window.__USER_INFO__",
                "__INITIAL_STATE__.user.userInfo",
                "__NUXT__.data.0.userInfo",
            ]

            user_info = None
            for source in data_sources:
                logger.debug(f"从 {source} 获取用户信息...")
                result = await client.execute_tool("read_page_data", {
                    "path": source,
                    **tool_params
                }, timeout=15)
                logger.debug(f"{source} 结果: success={result.get('success')}, data={'有数据' if result.get('data') else '无数据'}")

                if result.get("success") and result.get("data"):
                    user_info = result.get("data")
                    logger.info(f"从 {source} 获取到数据, 类型: {type(user_info).__name__}, result : {result}")

                    # 如果是字符串，尝试解析为 JSON
                    if isinstance(user_info, str):
                        try:
                            import json
                            user_info = json.loads(user_info)
                            logger.debug(f"成功解析 JSON 字符串: {type(user_info).__name__}")
                        except (json.JSONDecodeError, ValueError):
                            logger.debug(f"无法解析为 JSON，保持字符串")
                            continue

                    # 处理 Vue ref 对象（包含 _rawValue 或 _value）
                    if isinstance(user_info, dict):
                        # Vue ref: 检查是否有 _rawValue 或 _value
                        if "_rawValue" in user_info:
                            user_info = user_info.get("_rawValue")
                            logger.debug(f"从 Vue ref._rawValue 提取: {type(user_info).__name__}")
                        elif "_value" in user_info:
                            user_info = user_info.get("_value")
                            logger.debug(f"从 Vue ref._value 提取: {type(user_info).__name__}")

                    # 提取嵌套的 userInfo（仅对未使用 _rawValue 的路径）
                    if "._rawValue" not in source and "._value" not in source and isinstance(user_info, dict):
                        if "userInfo" in user_info:
                            user_info = user_info.get("userInfo")
                        elif "user" in user_info and isinstance(user_info.get("user"), dict):
                            user_info = user_info.get("user")

                    # 确保 user_info 是 dict 类型
                    if isinstance(user_info, dict):
                        logger.debug(f"最终 user_info 包含的键: {list(user_info.keys())[:10]}")
                        break

            # 检查登录状态
            if user_info and isinstance(user_info, dict):
                # 检查各个可能的登录标识字段
                is_login = user_info.get("isLogin", False)
                is_logged_in_flag = user_info.get("isLoggedIn", False)
                login_flag = user_info.get("login")
                loggedIn_flag = user_info.get("loggedIn")
                uid_val = user_info.get("uid")
                userId_val = user_info.get("userId")
                is_guest = user_info.get("guest", False)  # guest=True 表示游客，未登录

                logger.debug(f"登录检查: isLogin={is_login}, isLoggedIn={is_logged_in_flag}, login={login_flag}, loggedIn={loggedIn_flag}, uid={uid_val}, userId={userId_val}, guest={is_guest}")

                # 如果是游客 (guest=True)，则未登录
                if is_guest:
                    logger.info("检测到 guest=True，表示用户未登录（仅游客访问）")
                    is_logged_in = False
                else:
                    is_logged_in = is_login or is_logged_in_flag or login_flag or loggedIn_flag or uid_val or userId_val

                if is_logged_in:
                    username = (
                        user_info.get("nickname") or
                        user_info.get("userName") or
                        user_info.get("name")
                    )
                    logger.info(f"方法2检测到已登录，用户: {username}")
                    return XHSCheckLoginStatusResult(
                        success=True,
                        is_logged_in=True,
                        username=username,
                        user_id=user_info.get("userId") or user_info.get("uid"),
                        avatar=user_info.get("avatar") or user_info.get("userImage"),
                        message=self._get_status_message({"is_logged_in": True, "username": username})
                    )

            # 未检测到登录，返回未登录
            logger.info("未检测到登录状态")
            return XHSCheckLoginStatusResult(
                success=True,
                is_logged_in=False,
                message="未检测到登录状态"
            )

        except Exception as e:
            logger.exception(f"检查登录状态时发生异常: {str(e)}")
            return XHSCheckLoginStatusResult(
                success=False,
                is_logged_in=False,
                message=f"检查登录状态失败: {str(e)}"
            )

    def _get_status_message(self, login_data: dict) -> str:
        """生成状态消息"""
        if login_data.get("is_logged_in"):
            username = login_data.get("username", "未知用户")
            return f"已登录，用户: {username}"
        else:
            return "未登录"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def check_login_status(
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSCheckLoginStatusResult:
    """
    便捷的登录检查函数

    Args:
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XHSCheckLoginStatusResult: 检查结果
    """
    tool = CheckLoginStatusTool()
    params = XHSCheckLoginStatusParams(tab_id=tab_id)
    ctx = context or ExecutionContext()

    logger.info(f"执行工具: {tool.name}, params={params}, ctx: {ctx}")

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSCheckLoginStatusResult(
            success=False,
            is_logged_in=False,
            message=f"检查失败: {result.error}"
        )


__all__ = [
    "CheckLoginStatusTool",
    "check_login_status",
    "XHSCheckLoginStatusParams",
    "XHSCheckLoginStatusResult",
]
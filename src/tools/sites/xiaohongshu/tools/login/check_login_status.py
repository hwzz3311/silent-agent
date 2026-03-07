"""
小红书登录检查工具

实现 xhs_check_login_status 工具，检查当前小红书登录状态。
"""

import logging
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.domain import business_tool
from src.tools.domain.base import BusinessTool
from src.tools.domain.logging import log_operation
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .types import XHSCheckLoginStatusParams, XHSCheckLoginStatusResult

# 创建日志记录器
logger = logging.getLogger("xhs_check_login_status")


@business_tool(
    name="xhs_check_login_status",
    site_type=XiaohongshuSite,
    param_type=XHSCheckLoginStatusParams,
    operation_category="login"
)
class CheckLoginStatusTool(BusinessTool):
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
    required_login = False  # 此工具本身用于检查登录状态，不需要登录

    # 直接模式类属性
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/"

    @log_operation("xhs_check_login_status")
    async def _execute_core(
        self,
        params: XHSCheckLoginStatusParams,
        context: ExecutionContext,
    ) -> Any:
        """
        核心执行逻辑 - 通过 context 获取的 client 执行浏览器操作

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）

        Returns:
            XHSCheckLoginStatusResult: 检查结果
        """
        logger.info("开始检查小红书登录状态")
        logger.debug(f"参数: tab_id={params.tab_id}")

        # 使用 context.client（依赖注入）
        client = context.client
        if not client:
            return XHSCheckLoginStatusResult(
                success=False,
                is_logged_in=False,
                message="无法获取浏览器客户端，请确保通过 API 调用"
            )

        # 使用 client 执行读取操作
        try:
            # 使用基类的 ensure_site_tab 方法获取有效标签页
            tab_id = await self.ensure_site_tab(
                client=client,
                context=context,
                fallback_url="https://www.xiaohongshu.com/",
                params_tab_id=params.tab_id
            )

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
                            logger.debug("无法解析为 JSON，保持字符串")
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

    result = await tool.execute(params, ctx)

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
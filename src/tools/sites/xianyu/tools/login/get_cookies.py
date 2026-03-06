"""
闲鱼获取 Cookie 工具

实现 xianyu_get_cookies 工具，从已登录的浏览器会话中提取 Cookie。
"""

import logging
from typing import Any

from src.tools.base import ExecutionContext

from src.tools.domain import business_tool
from src.tools.domain.base import BusinessTool
from src.tools.domain.logging import log_operation
from src.tools.domain.site_base import Site
from src.tools.sites.xianyu.adapters import XianyuSite
from .types import GetCookiesParams
from .types import GetCookieResult

# 创建日志记录器
logger = logging.getLogger("xianyu_get_cookies")


@business_tool(name="xianyu_get_cookies", site_type=XianyuSite, param_type=GetCookiesParams, operation_category="login")
class GetCookiesTool(BusinessTool):
    """
    获取闲鱼 Cookie

    使用已登录的浏览器会话，获取当前登录用户的 Cookie。
    返回 Cookie 字典 {name: value}。

    Usage:
        tool = GetCookiesTool()
        result = await tool.execute(
            params=GetCookiesParams(),
            context=context
        )

        if result.success:
            print(f"Cookie: {result.data.cookie}")
            print(f"已登录: {result.data.is_logged_in}")
    """

    name = "xianyu_get_cookies"
    description = "获取闲鱼已登录用户的 Cookie，返回 Cookie 字典"
    version = "1.0.0"
    category = "xianyu"
    operation_category = "login"
    site_type = XianyuSite
    required_login = False  # 此工具用于获取 Cookie，不需要预先登录（但需要浏览器会话）

    # 使用基类的 tab 管理抽象
    target_site_domain = "goofish.com"
    default_navigate_url = "https://www.goofish.com"

    @log_operation("xianyu_get_cookies")
    async def _execute_core(
        self,
        params: GetCookiesParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑 - 通过已存在的浏览器客户端获取 Cookie

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）
            site: 网站适配器实例

        Returns:
            GetCookiesResult: 获取结果
        """
        logger.info("开始获取闲鱼 Cookie")

        # 尝试从 context 获取 client
        client = getattr(context, 'client', None)
        logger.debug(f"从 context 获取 client: {client is not None}")

        if not client:
            logger.error("无法获取浏览器客户端，请确保浏览器已启动")
            return GetCookiesResult(
                success=False,
                is_logged_in=False,
                message="无法获取浏览器客户端，请确保浏览器已启动"
            )

        try:
            # ========== 使用 ensure_site_tab 获取标签页 ==========
            # 优先使用参数中的 tab_id，否则使用 context 中的 tab_id
            # fallback_url 优先使用参数中的 target_url，否则使用默认导航 URL
            fallback_url = params.target_url or self.default_navigate_url
            tab_id = await self.ensure_site_tab(
                client=client,
                context=context,
                fallback_url=fallback_url,
                params_tab_id=params.tab_id
            )

            # 如果还是没有 tab_id，尝试不指定 tab_id直接操作
            if not tab_id:
                logger.warning("无法获取标签页，尝试不指定 tab_id")

            # 等待页面加载
            import asyncio
            await asyncio.sleep(2)

            # 步骤1: 检测登录状态
            logger.info("开始检测登录状态...")
            is_logged_in = False
            username = None
            user_id = None

            # 使用多种方式检测登录状态
            login_check_js = """
            (function() {
                // 方法1: 检查用户头像元素
                const avatarSelectors = [
                    '.user-avatar img',
                    '.avatar img',
                    '[class*="user-avatar"] img',
                    '[class*="avatar"] img',
                    '.header-avatar img',
                    '.login-user-avatar img',
                    '.user-info img',
                    '.mine-avatar img'
                ];

                for (const selector of avatarSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.src && el.src.length > 0 && !el.src.includes('default')) {
                        return { is_logged_in: true, avatar: el.src, method: 'avatar' };
                    }
                }

                // 方法2: 检查用户名元素
                const usernameSelectors = [
                    '.username',
                    '.nickname',
                    '.user-name',
                    '[class*="user-name"]',
                    '[class*="nickname"]',
                    '.header-username',
                    '.user-nickname'
                ];

                for (const selector of usernameSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.textContent && el.textContent.trim()) {
                        const text = el.textContent.trim();
                        if (text.length > 0 && text.length < 50) {
                            return { is_logged_in: true, username: text, method: 'username' };
                        }
                    }
                }

                // 方法3: 检查登录/未登录相关元素
                const loginIndicatorSelectors = [
                    '.login-btn',
                    '.login-link',
                    '.not-login',
                    '.unlogin'
                ];

                for (const selector of loginIndicatorSelectors) {
                    const el = document.querySelector(selector);
                    if (el) {
                        return { is_logged_in: false, method: 'login-indicator' };
                    }
                }

                // 方法4: 检查顶部用户信息栏
                const headerUserSelectors = [
                    '.header-user',
                    '.header-user-info',
                    '.top-user-info',
                    '.user-panel'
                ];

                for (const selector of headerUserSelectors) {
                    const el = document.querySelector(selector);
                    if (el && el.children && el.children.length > 0) {
                        return { is_logged_in: true, method: 'header-user' };
                    }
                }

                return { is_logged_in: false, method: 'none' };
            })()
            """

            tool_params = {"timeout": 10000}
            if tab_id:
                tool_params["tabId"] = tab_id

            login_result = await client.execute_tool("read_page_data", {
                "path": login_check_js,
                **tool_params
            }, timeout=15000)

            logger.debug(f"登录检测结果: {login_result}")

            if login_result.get("success") and login_result.get("data"):
                login_data = login_result.get("data")
                if isinstance(login_data, dict):
                    is_logged_in = login_data.get("is_logged_in", False)
                    username = login_data.get("username")
                    avatar = login_data.get("avatar")
                    logger.info(f"登录状态检测: is_logged_in={is_logged_in}, username={username}, method={login_data.get('method')}")

            # 如果未登录，返回错误
            if not is_logged_in:
                logger.warning("用户未登录，无法获取 Cookie")
                return GetCookiesResult(
                    success=False,
                    is_logged_in=False,
                    message="用户未登录，请先完成登录后再获取 Cookie"
                )

            # 步骤2: 获取 Cookie
            logger.info("用户已登录，开始获取 Cookie...")

            # 使用 JavaScript 获取所有 Cookie
            get_cookies_js = """
            (function() {
                const cookieStr = document.cookie;
                if (!cookieStr) {
                    return { cookies: {}, message: "No cookies found" };
                }

                const cookies = {};
                cookieStr.split(';').forEach(cookie => {
                    const parts = cookie.split('=');
                    if (parts.length >= 2) {
                        const name = parts[0].trim();
                        const value = parts.slice(1).join('=').trim();
                        cookie[name] = value;
                    }
                });

                return {
                    cookies: cookie,
                    count: Object.keys(cookie).length,
                    domains: window.location.hostname
                };
            })()
            """

            cookie_result = await client.execute_tool("read_page_data", {
                "path": get_cookies_js,
                **tool_params
            }, timeout=10000)

            logger.debug(f"Cookie 获取结果: {cookie_result}")

            cookies_dict = {}
            if cookie_result.get("success") and cookie_result.get("data"):
                data = cookie_result.get("data")
                if isinstance(data, dict):
                    cookie_dict = data.get("cookies", {})
                    logger.info(f"成功获取 {len(cookie_dict)} 个 Cookie")
                else:
                    logger.warning(f"Cookie 数据格式异常: {type(data)}")
            else:
                logger.warning(f"获取 Cookie 失败: {cookie_result.get('error')}")

            # 过滤掉敏感或无用的 Cookie（可选）
            # 这里保留所有 Cookie，由调用方自行处理

            # 返回成功结果
            return GetCookiesResult(
                success=True,
                cookie=cookie_dict,
                is_logged_in=True,
                username=username,
                user_id=user_id,
                message=f"成功获取 {len(cookie_dict)} 个 Cookie"
            )

        except Exception as e:
            logger.exception(f"获取 Cookie 时发生异常: {str(e)}")
            return GetCookiesResult(
                success=False,
                is_logged_in=False,
                message=f"获取 Cookie 失败: {str(e)}"
            )

# 便捷函数
async def get_cookies(
    tab_id: int = None,
    target_url: str = None,
    context: ExecutionContext = None
) -> GetCookieResult:
    """
    便捷的获取 Cookie 函数

    Args:
        tab_id: 标签页 ID
        target_url: 目标 URL
        context: 执行上下文

    Returns:
        GetCookiesResult: 获取结果
    """
    tool = GetCookiesTool()
    params = GetCookiesParams(tab_id=tab_id, target_url=target_url)
    ctx = context or ExecutionContext()

    logger.info(f"执行工具: {tool.name}, params={params}, ctx: {ctx}")

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return GetCookiesResult(
            success=False,
            is_logged_in=False,
            message=f"获取失败: {result.error}"
        )


__all__ = [
    "GetCookiesTool",
    "get_cookies",
    "GetCookiesParams",
    "GetCookiesResult",
]

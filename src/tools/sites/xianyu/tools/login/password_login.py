"""
闲鱼密码登录工具

实现 xianyu_password_login 工具，使用账号密码登录闲鱼。
"""

import logging
import time
import random
import os
from typing import Any, Optional, Dict

from src.tools.base import ExecutionContext

from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xianyu.adapters import XianyuSite, XianyuSliderSolver

from .params import PasswordLoginParams
from .result import PasswordLoginResult

# 创建日志记录器
logger = logging.getLogger("xianyu_password_login")


class PasswordLoginTool(BusinessTool[XianyuSite, PasswordLoginParams]):
    """
    闲鱼密码登录工具

    使用账号密码登录闲鱼，支持滑块验证处理。

    Usage:
        tool = PasswordLoginTool()
        result = await tool.execute(
            params=PasswordLoginParams(
                account="13800138000",
                password="password123",
                headless=True
            ),
            context=context
        )

        if result.success:
            print(f"登录成功，Cookie: {result.data.cookie}")
    """

    name = "xianyu_password_login"
    description = "使用账号密码登录闲鱼，支持滑块验证处理"
    version = "1.0.0"
    category = "xianyu"
    operation_category = "login"
    site_type = XianyuSite
    required_login = False  # 登录工具本身不需要登录

    @log_operation("xianyu_password_login")
    async def _execute_core(
        self,
        params: PasswordLoginParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑 - 使用 Playwright 进行密码登录

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）
            site: 网站适配器实例

        Returns:
            PasswordLoginResult: 登录结果
        """
        logger.info("开始闲鱼密码登录流程")
        logger.info(f"账号: {params.account}")
        logger.info(f"无头模式: {params.headless}")

        # 尝试获取 client
        client = getattr(context, 'client', None)
        logger.debug(f"从 context 获取 client: {client is not None}")

        if not client:
            # 如果没有 client，抛出错误
            logger.error("无法获取浏览器客户端，请确保浏览器已启动")
            return PasswordLoginResult(
                success=False,
                message="无法获取浏览器客户端，请确保浏览器已启动"
            )

        try:
            # 步骤1: 导航到登录页面
            logger.info("步骤1: 导航到登录页面")
            nav_result = await client.execute_tool("chrome_navigate", {
                "url": "https://www.goofish.com/im",
                "newTab": False
            }, timeout=30000)

            if not nav_result.get("success"):
                logger.error(f"导航失败: {nav_result.get('error')}")
                return PasswordLoginResult(
                    success=False,
                    message=f"导航失败: {nav_result.get('error')}"
                )

            # 等待页面加载
            time.sleep(3)

            # 步骤2: 查找登录表单（主页面或 iframe）
            logger.info("步骤2: 查找登录表单")
            login_frame = await self._find_login_form(client)

            if not login_frame:
                # 检查是否已登录
                is_logged_in = await self._check_login_success(client)
                if is_logged_in:
                    logger.info("检测到已登录状态")
                    cookies = await self._extract_cookies(client)
                    return PasswordLoginResult(
                        success=True,
                        cookie=cookies,
                        message="已登录"
                    )

                logger.error("未找到登录表单")
                return PasswordLoginResult(
                    success=False,
                    message="未找到登录表单，请确保在登录页面"
                )

            # 步骤3: 点击密码登录标签
            logger.info("步骤3: 点击密码登录标签")
            await self._click_password_tab(client, login_frame)
            time.sleep(1)

            # 步骤4: 输入账号
            logger.info("步骤4: 输入账号")
            await self._input_account(client, login_frame, params.account)
            time.sleep(0.8)

            # 步骤5: 输入密码
            logger.info("步骤5: 输入密码")
            await self._input_password(client, login_frame, params.password)
            time.sleep(0.8)

            # 步骤6: 勾选用户协议
            logger.info("步骤6: 勾选用户协议")
            await self._check_agreement(client, login_frame)

            # 步骤7: 点击登录按钮
            logger.info("步骤7: 点击登录按钮")
            await self._click_login_button(client, login_frame)

            # 等待登录响应
            time.sleep(3)

            # 步骤8: 检测并处理滑块验证
            logger.info("步骤8: 检测滑块验证")
            slider_detected = await self._detect_slider(client)

            if slider_detected:
                logger.info("检测到滑块验证，开始处理")
                slider_success = await self._solve_slider(client)

                if not slider_success:
                    # 滑块处理失败，刷新重试
                    logger.warning("滑块处理失败，刷新页面重试")
                    await client.execute_tool("chrome_navigate", {
                        "url": "https://www.goofish.com/im",
                        "newTab": False
                    }, timeout=30000)
                    time.sleep(2)

                    slider_success = await self._solve_slider(client)
                    if not slider_success:
                        return PasswordLoginResult(
                            success=False,
                            message="滑块验证失败"
                        )

                logger.info("滑块验证成功")

            # 步骤9: 检查登录错误
            logger.info("步骤9: 检查登录错误")
            has_error, error_message = await self._check_login_error(client)

            if has_error:
                logger.error(f"登录失败: {error_message}")
                return PasswordLoginResult(
                    success=False,
                    message=error_message or "账号或密码错误"
                )

            # 步骤10: 检查登录状态
            logger.info("步骤10: 检查登录状态")
            time.sleep(3)  # 等待登录完成

            is_logged_in = await self._check_login_success(client)
            if not is_logged_in:
                # 再等待一段时间后重试
                time.sleep(5)
                is_logged_in = await self._check_login_success(client)

            if not is_logged_in:
                return PasswordLoginResult(
                    success=False,
                    message="登录状态未确认，请检查账号密码是否正确"
                )

            # 步骤11: 提取 Cookie
            logger.info("步骤11: 提取 Cookie")
            cookies = await self._extract_cookies(client)

            if not cookies:
                return PasswordLoginResult(
                    success=False,
                    message="获取 Cookie 失败"
                )

            logger.success("登录成功")
            return PasswordLoginResult(
                success=True,
                cookie=cookies,
                message="登录成功"
            )

        except Exception as e:
            logger.exception(f"登录过程发生异常: {str(e)}")
            return PasswordLoginResult(
                success=False,
                message=f"登录失败: {str(e)}"
            )

    async def _find_login_form(self, client) -> Optional[Dict]:
        """
        查找登录表单（主页面或 iframe）

        Args:
            client: 浏览器客户端

        Returns:
            登录表单上下文（page 或 frame），未找到返回 None
        """
        # 主页面登录表单选择器
        main_selectors = [
            '#fm-login-id',
            'input[name="fm-login-id"]',
            'input[placeholder*="手机号"]',
            'input[placeholder*="邮箱"]',
            '.fm-login-id'
        ]

        logger.info("查找主页面登录表单")
        for selector in main_selectors:
            result = await client.execute_tool("read_page_data", {
                "path": f"document.querySelector('{selector}') !== null"
            }, timeout=5000)

            if result.get("success") and result.get("data"):
                logger.info(f"在主页面找到登录表单: {selector}")
                return {"type": "main", "page": "main"}

        # 查找 iframe
        logger.info("查找 iframe")
        result = await client.execute_tool("read_page_data", {
            "path": """
            (function() {
                var iframes = document.querySelectorAll('iframe');
                var result = [];
                for (var i = 0; i < iframes.length; i++) {
                    var iframe = iframes[i];
                    result.push({
                        index: i,
                        src: iframe.src || '',
                        id: iframe.id || '',
                        name: iframe.name || ''
                    });
                }
                return result;
            })()
            """
        }, timeout=5000)

        iframes = result.get("data", []) if result.get("success") else []
        logger.info(f"找到 {len(iframes)} 个 iframe")

        # 检查 iframe 中是否有登录表单
        for iframe_info in iframes:
            # 尝试访问 iframe 内容
            # 由于 Playwright 的限制，我们直接在主页面查找
            for selector in main_selectors:
                result = await client.execute_tool("read_page_data", {
                    "path": f"""
                    (function() {{
                        var iframes = document.querySelectorAll('iframe');
                        for (var i = 0; i < iframes.length; i++) {{
                            try {{
                                var doc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                                var el = doc.querySelector('{selector}');
                                if (el) return i;
                            }} catch(e) {{}}
                        }}
                        return -1;
                    }})()
                    """
                }, timeout=5000)

                if result.get("success") and result.get("data", -1) >= 0:
                    logger.info(f"在 iframe {result.get('data')} 中找到登录表单")
                    return {"type": "iframe", "index": result.get("data")}

        return None

    async def _click_password_tab(self, client, login_frame: Dict):
        """
        点击密码登录标签

        Args:
            client: 浏览器客户端
            login_frame: 登录表单上下文
        """
        selectors = [
            "a.password-login-tab-item",
            ".password-login-tab-item",
            "text=密码登录"
        ]

        for selector in selectors:
            result = await client.execute_tool("read_page_data", {
                "path": f"""
                (function() {{
                    var el = document.querySelector('{selector}');
                    if (el && el.offsetParent !== null) {{
                        el.click();
                        return true;
                    }}
                    return false;
                }})()
                """
            }, timeout=5000)

            if result.get("success") and result.get("data"):
                logger.info(f"点击密码登录标签成功: {selector}")
                return

        logger.warning("未找到密码登录标签")

    async def _input_account(self, client, login_frame: Dict, account: str):
        """
        输入账号

        Args:
            client: 浏览器客户端
            login_frame: 登录表单上下文
            account: 账号
        """
        selectors = "#fm-login-id"

        result = await client.execute_tool("read_page_data", {
            "path": f"""
            (function() {{
                var el = document.querySelector('{selectors}');
                if (el) {{
                    el.value = '{account}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubble: true }}));
                    return true;
                }}
                return false;
            }})()
            """
        }, timeout=5000)

        if result.get("success") and result.get("data"):
            logger.info("账号输入成功")
        else:
            logger.error("账号输入失败")

    async def _input_password(self, client, login_frame: Dict, password: str):
        """
        输入密码

        Args:
            client: 浏览器客户端
            login_frame: 登录表单上下文
            password: 密码
        """
        selector = "#fm-login-password"

        result = await client.execute_tool("read_page_data", {
            "path": f"""
            (function() {{
                var el = document.querySelector('{selector}');
                if (el) {{
                    el.value = '{password}';
                    el.dispatchEvent(new Event('input', {{ bubble: true }}));
                    el.dispatchEvent(new Event('change', {{ bubble: true }}));
                    return true;
                }}
                return false;
            }})()
            """
        }, timeout=5000)

        if result.get("success") and result.get("data"):
            logger.info("密码输入成功")
        else:
            logger.error("密码输入失败")

    async def _check_agreement(self, client, login_frame: Dict):
        """
        勾选用户协议

        Args:
            client: 浏览器客户端
            login_frame: 登录表单上下文
        """
        selector = "#fm-agreement-checkbox"

        result = await client.execute_tool("read_page_data", {
            "path": f"""
            (function() {{
                var el = document.querySelector('{selector}');
                if (el && !el.checked) {{
                    el.click();
                    return true;
                }}
                return false;
            }})()
            """
        }, timeout=5000)

        if result.get("success") and result.get("data"):
            logger.info("用户协议勾选成功")
        else:
            logger.warning("用户协议勾选失败或已勾选")

    async def _click_login_button(self, client, login_frame: Dict):
        """
        点击登录按钮

        Args:
            client: 浏览器客户端
            login_frame: 登录表单上下文
        """
        selectors = [
            "button.password-login",
            ".password-login",
            'button[type="submit"]',
            "input[type='submit']"
        ]

        for selector in selectors:
            result = await client.execute_tool("read_page_data", {
                "path": f"""
                (function() {{
                    var el = document.querySelector('{selector}');
                    if (el && el.offsetParent !== null) {{
                        el.click();
                        return true;
                    }}
                    return false;
                }})()
                """
            }, timeout=5000)

            if result.get("success") and result.get("data"):
                logger.info(f"点击登录按钮成功: {selector}")
                return

        logger.error("未找到登录按钮")

    async def _detect_slider(self, client) -> bool:
        """
        检测滑块验证

        Args:
            client: 浏览器客户端

        Returns:
            bool: 是否检测到滑块
        """
        slider_selectors = [
            "#nc_1_n1z",
            ".nc-container",
            ".nc_scale",
            ".nc-wrapper"
        ]

        for selector in slider_selectors:
            result = await client.execute_tool("read_page_data", {
                "path": f"""
                (function() {{
                    var el = document.querySelector('{selector}');
                    return el && el.offsetParent !== null;
                }})()
                """
            }, timeout=5000)

            if result.get("success") and result.get("data"):
                logger.info(f"检测到滑块验证元素: {selector}")
                return True

        return False

    async def _solve_slider(self, client, max_retries: int = 3) -> bool:
        """
        处理滑块验证

        Args:
            client: 浏览器客户端
            max_retries: 最大重试次数

        Returns:
            bool: 是否成功
        """
        slider_selectors = [
            "#nc_1_n1z",
            ".nc-container .nc-slider",
            ".nc_scale"
        ]

        for attempt in range(1, max_retries + 1):
            logger.info(f"尝试处理滑块验证 (第{attempt}/{max_retries}次)")

            # 获取滑块按钮和滑道元素
            result = await client.execute_tool("read_page_data", {
                "path": """
                (function() {
                    var btn = document.querySelector('#nc_1_n1z');
                    var track = document.querySelector('.nc_scale') || document.querySelector('.nc_wrapper');
                    if (!btn || !track) return null;

                    var btnBox = btn.getBoundingClientRect();
                    var trackBox = track.getBoundingClientRect();

                    return {
                        btnX: btnBox.x,
                        btnY: btnBox.y,
                        btnW: btnBox.width,
                        btnH: btnBox.height,
                        trackW: trackBox.width,
                        trackX: trackBox.x
                    };
                })()
                """
            }, timeout=5000)

            if not result.get("success") or not result.get("data"):
                logger.warning("获取滑块元素信息失败")
                continue

            slider_info = result.get("data")
            if not slider_info:
                continue

            # 计算滑动距离（留一点余量）
            slide_distance = int(slider_info.get("trackW", 300) * 0.9)
            start_x = slider_info.get("btnX", 0) + slider_info.get("btnW", 0) / 2
            start_y = slider_info.get("btnY", 0) + slider_info.get("btnH", 0) / 2

            logger.info(f"滑块信息: 距离={slide_distance}, 起始位置=({start_x}, {start_y})")

            # 执行分段滑动（模拟人类操作）
            segments = 5
            segment_distance = slide_distance // segments

            # 先移动到按钮位置
            await client.execute_tool("mouse_move", {
                "x": start_x,
                "y": start_y
            }, timeout=5000)

            await client.execute_tool("mouse_down", {}, timeout=5000)

            current_x = start_x
            for i in range(segments):
                actual_segment = segment_distance + random.randint(-10, 10)
                current_x += actual_segment

                await client.execute_tool("mouse_move", {
                    "x": current_x,
                    "y": start_y + random.randint(-2, 2)
                }, timeout=5000)

                time.sleep(random.uniform(0.1, 0.2))

            await client.execute_tool("mouse_up", {}, timeout=5000)

            # 等待验证结果
            time.sleep(1.5)

            # 检查是否还有滑块（验证可能成功或失败）
            has_slider = await self._detect_slider(client)
            if not has_slider:
                logger.info("滑块验证成功")
                return True
            else:
                logger.warning("滑块验证失败，继续重试")

        return False

    async def _check_login_error(self, client) -> tuple:
        """
        检查登录错误

        Args:
            client: 浏览器客户端

        Returns:
            tuple: (has_error, error_message)
        """
        error_selectors = [
            '.login-error-msg',
            '[class*="error-msg"]',
            '[class*="error"]'
        ]

        for selector in error_selectors:
            result = await client.execute_tool("read_page_data", {
                "path": f"""
                (function() {{
                    var el = document.querySelector('{selector}');
                    if (el && el.offsetParent !== null) {{
                        return el.innerText || el.textContent;
                    }}
                    return null;
                }})()
                """
            }, timeout=5000)

            if result.get("success") and result.get("data"):
                error_text = result.get("data")
                if error_text and "错误" in error_text:
                    logger.error(f"检测到登录错误: {error_text}")
                    return True, error_text

        return False, None

    async def _check_login_success(self, client) -> bool:
        """
        检查登录是否成功

        Args:
            client: 浏览器客户端

        Returns:
            bool: 是否登录成功
        """
        # 使用页面元素检测登录成功
        selector = ".rc-virtual-list-holder-inner"

        result = await client.execute_tool("read_page_data", {
            "path": f"""
            (function() {{
                var el = document.querySelector('{selector}');
                if (el && el.offsetParent !== null) {{
                    return el.children.length > 0;
                }}
                return false;
            }})()
            """
        }, timeout=5000)

        if result.get("success") and result.get("data"):
            if result.get("data"):
                logger.info("检测到登录成功元素")
                return True

        # 后备方案：检查是否有用户信息元素
        backup_selectors = [
            ".user-info",
            ".user-name",
            ".user-avatar",
            "[class*='userInfo']"
        ]

        for selector in backup_selectors:
            result = await client.execute_tool("read_page_data", {
                "path": f"""
                (function() {{
                    var el = document.querySelector('{selector}');
                    return el && el.offsetParent !== null;
                }})()
                """
            }, timeout=5000)

            if result.get("success") and result.get("data"):
                logger.info(f"检测到用户信息元素: {selector}")
                return True

        return False

    async def _extract_cookies(self, client) -> Dict[str, str]:
        """
        提取 Cookie

        Args:
            client: 浏览器客户端

        Returns:
            Dict[str, str]: Cookie 字典 {name: value}
        """
        result = await client.execute_tool("get_cookies", {}, timeout=10000)

        if result.get("success") and result.get("data"):
            cookies_list = result.get("data", [])
            cookie_dict = {}
            for cookie in cookies_list:
                name = cookie.get("name", "")
                value = cookie.get("value", "")
                if name:
                    cookie_dict[name] = value

            logger.info(f"成功获取 Cookie，包含 {len(cookie_dict)} 个字段")
            return cookie_dict
        else:
            logger.error(f"获取 Cookie 失败: {result.get('error')}")
            return {}

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


__all__ = [
    "PasswordLoginTool",
]

"""
小红书获取登录二维码工具

实现 xhs_get_login_qrcode 工具，获取小红书登录二维码。
"""

import logging
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business import business_tool
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite
from .params import XHSGetLoginQrcodeParams
from .result import XHSGetLoginQrcodeResult

# 创建日志记录器
logger = logging.getLogger("xhs_get_login_qrcode")


@business_tool(name="xhs_get_login_qrcode", site_type=XiaohongshuSite, operation_category="login")
class GetLoginQrcodeTool(BusinessTool[XiaohongshuSite, XHSGetLoginQrcodeParams]):
    """
    获取小红书登录二维码

    返回登录二维码图片 URL 和数据，支持自动刷新。

    Usage:
        tool = GetLoginQrcodeTool()
        result = await tool.execute(
            params=XHSGetLoginQrcodeParams(),
            context=context
        )

        if result.success:
            print(f"二维码 URL: {result.data.qrcode_url}")
    """

    name = "xhs_get_login_qrcode"
    description = "获取小红书登录二维码，支持自动刷新"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "login"
    site_type = XiaohongshuSite
    required_login = False  # 此工具用于获取登录二维码，不需要已登录

    # 使用基类的 tab 管理抽象
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/"

    @log_operation("xhs_get_login_qrcode")
    async def _execute_core(
        self,
        params: XHSGetLoginQrcodeParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑 - 参考 check_login_status.py 的多选择器遍历方式

        Args:
            params: 工具参数
            context: 执行上下文
            site: 网站适配器实例

        Returns:
            XHSGetLoginQrcodeResult: 获取结果
        """
        import asyncio
        import time as time_module

        logger.info("开始获取小红书登录二维码")
        logger.debug(f"参数: tab_id={params.tab_id}")

        # 从 context 获取 client
        client = getattr(context, 'client', None)
        if not client:
            return XHSGetLoginQrcodeResult(
                success=False,
                message="无法获取浏览器客户端"
            )

        # 小红书域名
        # 使用基类的 ensure_site_tab 方法获取有效标签页
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url=self.default_navigate_url,
            params_tab_id=params.tab_id
        )

        # 如果还是没有 tab_id，抛出错误
        if not tab_id:
            logger.error("无法获取或创建标签页，浏览器可能未打开")
            return XHSGetLoginQrcodeResult(
                success=False,
                message="无法获取或创建标签页，请确保浏览器已打开"
            )

        logger.debug(f"最终使用的 tab_id: {tab_id}")

        # 等待页面加载
        await asyncio.sleep(3)

        # 只传递 tabId，不传递 timeout（避免参数冲突）
        tool_params = {"tabId": tab_id}

        # 二维码选择器列表 - 参考 check_login_status.py 的多选择器遍历方式
        qrcode_selectors = [
            "#app > div:nth-child(1) > div > div.login-container > div.left > div.code-area > div.qrcode.force-light > img",
            "#app > div > div > div.login-container > div.left > div.code-area > div.qrcode > img",
            ".qrcode.force-light img",
            ".code-area .qrcode img",
            "img.qrcode-img",
            "[class*='qrcode'] img",
            "[class*='login'] img",
        ]

        logger.info(f"开始检测二维码元素，共 {len(qrcode_selectors)} 个选择器")

        # 遍历每个选择器检测二维码 - 使用 inject_script 执行 JavaScript
        for selector in qrcode_selectors:
            # 步骤1: 检查元素是否存在
            check_code = "document.querySelector('" + selector + "') !== null"
            result = await client.execute_tool("inject_script", {
                "code": check_code,
                **tool_params
            }, timeout=1500)
            logger.info(f"执行：{check_code}；对应result : {result}")
            logger.debug(f"选择器 {selector} 是否存在: {result.get('data')}")

            # 步骤2: 如果存在，获取 src 属性
            if result.get("success") and result.get("data") is True:
                logger.info(f"检测到二维码元素: {selector}")

                # 元素存在，获取 src 属性
                js_code = "var el = document.querySelector('" + selector + "'); el ? (el.src || el.getAttribute('src')) : null"
                src_result = await client.execute_tool("inject_script", {
                    "code": js_code,
                    **tool_params
                }, timeout=1500)
                logger.info(f"获取src结果: {src_result}")

                if src_result.get("success") and src_result.get("data"):
                    qrcode_url = src_result.get("data")
                    if qrcode_url:
                        expire_timestamp = int(time_module.time()) + 300
                        logger.info(f"成功获取二维码: {qrcode_url[:80] if len(str(qrcode_url)) > 80 else qrcode_url}")
                        return XHSGetLoginQrcodeResult(
                            success=True,
                            qrcode_url=qrcode_url,
                            qrcode_data=None,
                            expire_time=expire_timestamp,
                            message="二维码已生成，请使用微信扫描登录"
                        )

        # 未找到二维码
        logger.warning("未检测到二维码元素")
        return XHSGetLoginQrcodeResult(
            success=False,
            qrcode_url=None,
            qrcode_data=None,
            expire_time=int(time_module.time()) + 300,
            message="未检测到二维码元素，请确保浏览器已打开小红书登录页面"
        )

    async def _is_tab_valid(self, client, tab_id: int) -> bool:
        """
        检测标签页是否还可用

        通过尝试读取页面标题来判断 tab 是否有效

        Args:
            client: 浏览器客户端
            tab_id: 标签页 ID

        Returns:
            bool: tab 是否有效
        """
        try:
            # 尝试读取页面标题，如果 tab 已关闭会失败
            result = await client.execute_tool("read_page_data", {
                "path": "document.title",
                "tabId": tab_id
            }, timeout=5000)

            is_valid = result.get("success", False)
            logger.debug(f"检测 tab_id={tab_id} 是否有效: {is_valid}")
            return is_valid
        except Exception as e:
            logger.debug(f"检测 tab_id={tab_id} 有效性失败: {e}")
            return False

    def _get_qrcode_message(self, qrcode_data: dict) -> str:
        """生成二维码状态消息"""
        if qrcode_data.get("qrcode_url") or qrcode_data.get("qrcode_data"):
            expire_time = qrcode_data.get("expire_time")
            if expire_time:
                import time
                remaining = int(expire_time - time.time())
                if remaining > 0:
                    return f"二维码已生成，有效期约 {remaining} 秒"
            return "二维码已生成，请使用微信扫描登录"
        else:
            return "无法获取登录二维码"



# 便捷函数
async def get_login_qrcode(
    tab_id: int = None,
    auto_refresh: bool = True,
    refresh_interval: int = 60,
    context: ExecutionContext = None
) -> XHSGetLoginQrcodeResult:
    """
    便捷的获取登录二维码函数

    Args:
        tab_id: 标签页 ID
        auto_refresh: 是否自动刷新
        refresh_interval: 刷新间隔（秒）
        context: 执行上下文

    Returns:
        XHSGetLoginQrcodeResult: 获取结果
    """
    tool = GetLoginQrcodeTool()
    params = XHSGetLoginQrcodeParams(
        tab_id=tab_id,
        auto_refresh=auto_refresh,
        refresh_interval=refresh_interval
    )
    ctx = context or ExecutionContext()
    logger.info(f"执行工具: {tool.name}, params={params}, ctx: {ctx}")
    result = await tool.execute_with_retry(params, ctx)
    logger.info(f" get_login_qrcode 工具执行结果: {result}")

    if result.success:
        return result.data
    else:
        return XHSGetLoginQrcodeResult(
            success=False,
            message=f"获取失败: {result.error}"
        )


__all__ = [
    "GetLoginQrcodeTool",
    "get_login_qrcode",
    "XHSGetLoginQrcodeParams",
    "XHSGetLoginQrcodeResult",
]
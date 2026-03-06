"""
闲鱼网站适配器

实现 Site 抽象基类，提供闲鱼特定的 RPA 操作。
"""

from typing import TYPE_CHECKING, Optional, Dict, Any, List

if TYPE_CHECKING:
    from src.tools.base import ExecutionContext

from src.tools.base import ExecutionContext
from src.core.result import Result, Error

from src.tools.domain.site_base import Site, SiteConfig, SiteSelectorSet, PageInfo
from src.tools.domain.errors import BusinessException


class XianyuSiteConfig(SiteConfig):
    """
    闲鱼网站配置

    Attributes:
        site_name: 网站标识
        base_url: 基础 URL
        timeout: 默认超时
        retry_count: 重试次数
        need_login: 是否需要登录
    """
    site_name: str = "xianyu"
    base_url: str = "https://www.goofish.com"
    timeout: int = 30000
    retry_count: int = 3
    need_login: bool = True


class XianyuSelectors(SiteSelectorSet):
    """
    闲鱼选择器集合

    继承通用选择器集合，添加闲鱼特定的 CSS 选择器。
    """

    # ========== 登录相关选择器 ==========
    login_button: str = ".login-btn"
    logout_button: str = ".logout-btn"
    user_avatar: str = ".user-avatar"
    username_display: str = ".username"
    login_form: str = "#fm-login-id"
    login_form_alt: str = 'input[name="fm-login-id"]'
    login_form_alt2: str = 'input[placeholder*="手机号"]'
    login_form_alt3: str = 'input[placeholder*="邮箱"]'
    password_input: str = "#fm-login-password"
    password_tab: str = "a.password-login-tab-item"
    login_submit: str = "button.password-login"
    agreement_checkbox: str = "#fm-agreement-checkbox"

    # ========== 滑块验证选择器 ==========
    slider_nc: str = "#nc_1_n1z"
    slider_container: str = ".nc-container"
    slider_scale: str = ".nc_scale"
    slider_wrapper: str = ".nc-wrapper"

    # ========== 登录成功检测选择器 ==========
    login_success: str = ".rc-virtual-list-holder-inner"

    # ========== 登录错误选择器 ==========
    error_msg: str = ".login-error-msg"
    error_msg_alt: str = '[class*="error-msg"]'

    # ========== 弹窗/对话框选择器 ==========
    modal_overlay: str = ".modal-overlay, .overlay"
    confirm_button: str = ".confirm-btn, .el-button--primary"
    cancel_button: str = ".cancel-btn, .el-button--default"
    close_button: str = ".close-btn, .el-dialog__close"
    cookie_accept_button: str = ".cookie-accept, .cookie-agree"

    # ========== 搜索相关选择器 ==========
    search_input: str = "input.search-input--WY2l9QD3, input[class*='search-input']"
    search_button: str = "button.search-icon--bewLHteU, button[class*='search-icon'], [class*='search'] button"
    search_result_container: str = "[class*='goods-list'], [class*='result-list']"
    search_item_link: str = "a[href*='/item?']"
    pagination_next: str = "[class*='pagination'] a, [class*='page'] a, [class*='next']"
    goods_price: str = "[class*='price']"
    goods_wants: str = "[class*='want'], [class*='wanted']"
    goods_image: str = "img[class*='cover'], img[class*='image']"


class XianyuSliderSolver:
    """
    闲鱼滑块验证处理工具

    实现闲鱼滑块验证的自动处理。
    """

    def __init__(self, page=None, context=None, browser=None):
        """
        初始化滑块处理工具

        Args:
            page: Playwright Page 对象
            context: Playwright Context 对象
            browser: Playwright Browser 对象
        """
        self.page = page
        self.context = context
        self.browser = browser

    def solve_slider(self, max_retries: int = 3) -> bool:
        """
        处理滑块验证

        Args:
            max_retries: 最大重试次数

        Returns:
            bool: 是否成功
        """
        import time
        import random

        slider_selectors = [
            '#nc_1_n1z',
            '.nc-container',
            '.nc_scale',
            '.nc-wrapper'
        ]

        for attempt in range(1, max_retries + 1):
            try:
                # 查找滑块元素
                slider_element = None
                for selector in slider_selectors:
                    try:
                        element = self.page.query_selector(selector)
                        if element and element.is_visible():
                            slider_element = element
                            break
                    except:
                        continue

                if not slider_element:
                    return False

                # 获取滑块滑块区域
                # 滑块通常是一个可以拖动的按钮
                button_element = self.page.query_selector('#nc_1_n1z')
                if not button_element:
                    return False

                # 计算滑动距离（通常为整个滑块条的长度）
                # 闲鱼滑块条的宽度通常是 300-350 像素
                # 我们需要滑动整个距离
                track_element = self.page.query_selector('.nc_scale')
                if not track_element:
                    track_element = self.page.query_selector('.nc_wrapper')

                # 计算滑动距离
                slide_distance = 300  # 默认值

                # 执行滑动操作（模拟人类操作，使用分段滑动）
                self._human_like_slide(button_element, slide_distance)

                # 等待验证结果
                time.sleep(1)

                # 检查是否验证成功
                # 如果滑块消失或出现成功提示，说明验证成功
                try:
                    error_box = self.page.query_selector('.ncaptcha')
                    if error_box and error_box.is_visible():
                        # 验证失败，继续重试
                        continue
                except:
                    pass

                return True

            except Exception as e:
                # 出错继续重试
                continue

        return False

    def _human_like_slide(self, button_element, distance: int):
        """
        模拟人类操作的滑动方式

        Args:
            button_element: 滑块按钮元素
            distance: 滑动距离（像素）
        """
        import random

        # 使用鼠标操作进行滑动
        # 先移动到按钮位置
        box = button_element.bounding_box()
        if not box:
            return

        start_x = box['x'] + box['width'] / 2
        start_y = box['y'] + box['height'] / 2

        # 模拟分段滑动（人类不会一次性滑完全程）
        # 将距离分成多个小段，每段之间有随机暂停
        segments = 5
        segment_distance = distance // segments

        current_x = start_x

        # 开始拖动
        self.page.mouse.move(start_x, start_y)
        self.page.mouse.down()

        for i in range(segments):
            # 每段滑动距离有随机变化
            actual_segment = segment_distance + random.randint(-10, 10)
            current_x += actual_segment

            # 添加随机抖动
            jitter_y = start_y + random.randint(-2, 2)

            self.page.mouse.move(current_x, jitter_y)

            # 段之间有短暂停顿
            import time
            time.sleep(random.uniform(0.05, 0.15))

        # 最后释放鼠标
        self.page.mouse.up()


class XianyuSite(Site):
    """
    闲鱼网站 RPA 操作适配器

    实现 Site 抽象基类的所有方法，提供闲鱼特定的 RPA 操作。

    Attributes:
        config: 闲鱼配置
        selector: 闲鱼选择器集合
    """

    config: XianyuSiteConfig = XianyuSiteConfig()
    selector: XianyuSelectors = XianyuSelectors()

    # ========== 页面类型定义 ==========

    PAGE_TYPES = [
        "home",      # 首页
        "login",    # 登录页
        "im",       # 消息页
        "profile",  # 用户主页
        "publish",  # 发布页
        "detail",   # 商品详情页
        "search",   # 搜索页
    ]

    # ========== 实现抽象方法 ==========

    async def check_login_status(
        self,
        context: 'ExecutionContext',
        silent: bool = False
    ) -> Result[Dict[str, Any]]:
        """
        检查登录状态

        Args:
            context: 执行上下文
            silent: 是否静默检查

        Returns:
            Result: 包含登录状态的字典
        """
        # 如果有 client，通过 client 执行检查
        client = getattr(context, 'client', None)
        if client:
            # 使用 client 执行检查
            pass

        # 返回未登录状态（由具体工具实现）
        return Result.ok({
            "is_logged_in": False,
            "message": "请调用登录工具"
        })

    async def navigate_to(
        self,
        context: 'ExecutionContext',
        page_type: str,
        **kwargs
    ) -> Result[PageInfo]:
        """
        导航到指定页面

        Args:
            context: 执行上下文
            page_type: 页面类型
            **kwargs: 额外参数

        Returns:
            Result: 页面信息
        """
        urls = {
            "home": f"{self.config.base_url}/",
            "login": f"{self.config.base_url}/im",
            "im": f"{self.config.base_url}/im",
            "profile": f"{self.config.base_url}/user/profile",
            "publish": f"{self.config.base_url}/publish",
            "search": f"{self.config.base_url}/search",
        }

        url = urls.get(page_type, self.config.base_url)

        # 如果有 client，通过 client 导航
        client = getattr(context, 'client', None)
        if client:
            await client.execute_tool("chrome_navigate", {
                "url": url,
                "newTab": False
            })

        return Result.ok(PageInfo(
            url=url,
            page_type=page_type,
            title=page_type
        ))

    async def wait_page_load(
        self,
        context: 'ExecutionContext',
        timeout: int = 30000
    ) -> Result[bool]:
        """
        等待页面加载完成

        Args:
            context: 执行上下文
            timeout: 超时时间（毫秒）

        Returns:
            Result: 是否加载成功
        """
        return Result.ok(True)

    async def close_popups(
        self,
        context: 'ExecutionContext'
    ) -> Result[bool]:
        """
        关闭弹窗

        Args:
            context: 执行上下文

        Returns:
            Result: 是否成功
        """
        return Result.ok(True)

    # ========== 发布相关方法 ==========

    async def publish_item(
        self,
        context: 'ExecutionContext' = None,
        price: str = None,
        description: str = None,
        images: list = None,
        category_index: int = 3
    ) -> Result[Dict[str, Any]]:
        """
        发布闲鱼商品

        Args:
            context: 执行上下文
            price: 商品价格
            description: 商品描述
            images: 图片路径列表
            category_index: 分类索引（默认3=其他技能服务）

        Returns:
            Result[Dict[str, Any]]: 发布结果，包含 item_id 和 url
        """
        from src.tools.primitives.fill import FillTool
        from src.tools.primitives.click import ClickTool
        from src.tools.primitives.evaluate import EvaluateTool
        import asyncio
        import os

        try:
            # 确保 context 存在
            ctx = context or self._create_default_context()
            client = getattr(ctx, 'client', None)

            if not client:
                return Result.fail(Error.new("未连接到浏览器，请先启动浏览器"))

            # 1. 导航到发布页面
            await self.navigate("publish", context=ctx)
            await asyncio.sleep(2)

            # 2. 填写价格
            fill_tool = FillTool()
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".ant-input",
                    value=price
                ),
                context=ctx
            )
            print(f"[xianyu_publish] 价格: {price}")

            # 3. 填写描述
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector="div[class^='editor--']",
                    value=description
                ),
                context=ctx
            )
            print(f"[xianyu_publish] 描述: {description}")

            # 4. 上传图片
            if images:
                for idx, image_path in enumerate(images[:9]):  # 最多9张
                    if os.path.exists(image_path):
                        # 使用 DataTransfer 方式上传文件
                        # 读取文件内容并转换为 base64
                        with open(image_path, 'rb') as f:
                            image_data = f.read()
                        import base64
                        img_data_b64 = base64.b64encode(image_data).decode('utf-8')
                        file_name = os.path.basename(image_path)
                        # 根据文件扩展名判断 mime 类型
                        ext = os.path.splitext(file_name)[1].lower()
                        mime_type = {
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.png': 'image/png',
                            '.gif': 'image/gif',
                            '.webp': 'image/webp'
                        }.get(ext, 'image/jpeg')

                        # 执行 JS 上传
                        eval_tool = EvaluateTool()
                        upload_script = f"""
                        (function() {{
                            const input = document.querySelector('input[name="file"]');
                            if (!input) return {{ success: false, error: 'input not found' }};

                            const blob = new Blob([new Uint8Array(atob("{img_data_b64}").split('').map(c => c.charCodeAt(0)))], {{ type: "{mime_type}" }});
                            const file = new File([blob], "{file_name}", {{ type: "{mime_type}" }});
                            const dt = new DataTransfer();
                            dt.items.add(file);
                            input.files = dt.files;
                            input.dispatchEvent(new Event('change', {{ bubble: true }}));
                            return {{ success: true }};
                        }})()
                        """
                        await eval_tool.execute(
                            params=EvaluateParams(code=upload_script, args=[]),
                            context=ctx
                        )
                        print(f"[xianyu_publish] 图片 {idx + 1} 已上传: {file_name}")
                        await asyncio.sleep(1)

            # 5. 选择分类
            await asyncio.sleep(1.5)

            # 检查是否出现"网页版暂不支持发布此分类"的警告
            check_unsupported_script = """
            (function() {
                return document.body.innerHTML.includes('网页版暂不支持发布此分类');
            })()
            """
            eval_tool = EvaluateTool()

            # 遍历分类直到找到支持的
            for i in range(category_index, 10):
                # 点击分类下拉框
                click_tool = ClickTool()
                await click_tool.execute(
                    params=click_tool._get_params_type()(
                        selector="div.ant-select-selector",
                        timeout=5000
                    ),
                    context=ctx
                )
                await asyncio.sleep(0.5)

                # 点击第 i 个分类选项
                select_script = f"""
                (function() {{
                    const options = document.querySelectorAll('div[class*="ant-select-item-option"]');
                    if (options[{i}]) {{
                        options[{i}].click();
                        return {{ success: true, index: {i} }};
                    }}
                    return {{ success: false, error: 'option not found' }};
                }})()
                """
                await eval_tool.execute(
                    params=EvaluateParams(code=select_script, args=[]),
                    context=ctx
                )
                await asyncio.sleep(0.5)

                # 检查是否还有不支持的警告
                result = await eval_tool.execute(
                    params=EvaluateParams(code=check_unsupported_script, args=[]),
                    context=ctx
                )
                if not result.data:
                    print(f"[xianyu_publish] 已选择分类 index: {i}")
                    break
                else:
                    print(f"[xianyu_publish] 分类 {i} 不支持网页发布，重新选择...")
            else:
                print("[xianyu_publish] 警告: 所有分类都不支持网页发布")

            await asyncio.sleep(0.5)

            # 6. 点击发布按钮
            publish_script = """
            (function() {
                const buttons = Array.from(document.querySelectorAll('button'));
                const publishBtn = buttons.find(b => b.textContent.includes('发布'));
                if (publishBtn) {
                    publishBtn.click();
                    return { success: true };
                }
                return { success: false, error: 'publish button not found' };
            })()
            """
            await eval_tool.execute(
                params=EvaluateParams(code=publish_script, args=[]),
                context=ctx
            )
            print("[xianyu_publish] 已点击发布按钮")

            # 等待发布完成
            await asyncio.sleep(3)

            # 7. 验证发布成功
            # 获取当前 URL 检查是否跳转到商品详情页
            from src.tools.primitives.navigate import GetUrlTool
            get_url_tool = GetUrlTool()
            url_result = await get_url_tool.execute(
                params=get_url_tool._get_params_type()(),
                context=ctx
            )
            current_url = url_result.data.get("url", "") if isinstance(url_result.data, dict) else ""

            print(f"[xianyu_publish] 当前 URL: {current_url}")

            # 检查 URL 是否包含 /item?id= (发布成功标志)
            if "/item?id=" in current_url:
                import re
                match = re.search(r'id=(\d+)', current_url)
                item_id = match.group(1) if match else None
                print(f"[xianyu_publish] 发布成功！商品ID: {item_id}")
                return Result.ok({
                    "item_id": item_id,
                    "url": current_url,
                })
            else:
                print("[xianyu_publish] 发布结果未明，请检查截图")
                return Result.ok({
                    "item_id": None,
                    "url": current_url,
                })

        except Exception as e:
            print(f"[xianyu_publish] 发布失败: {e}")
            return Result.fail(Error.from_exception(e))


__all__ = [
    "XianyuSite",
    "XianyuSiteConfig",
    "XianyuSelectors",
    "XianyuSliderSolver",
]

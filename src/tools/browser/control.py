"""
浏览器控制工具

提供各种浏览器控制功能，包括 Cookie 管理、页面操作、数据提取等。

该工具是对其他浏览器工具的整合封装，提供更高级别的浏览器控制操作。
"""

import asyncio
import logging
from typing import Optional, Any, Dict, List, Union
from pydantic import Field

from src.tools.base import Tool, ToolParameters, ExecutionContext, tool
from src.core.result import Result

logger = logging.getLogger("browser.control")


class ControlParams(ToolParameters):
    """
    浏览器控制参数

    Attributes:
        action: 控制操作类型
        params: 操作参数
    """
    action: str = Field(
        ...,
        description="控制操作类型",
        examples=["clear_cookies", "get_login_qrcode", "publish_content"]
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="操作参数"
    )


@tool(
    name="browser.control",
    description="浏览器控制工具，提供 Cookie 管理、页面操作、数据提取等高级功能",
    category="browser",
    version="1.0.0",
    tags=["browser", "control", "cookies", "publish", "login"]
)
class ControlTool(Tool[ControlParams, dict]):
    """浏览器控制工具"""

    async def execute(
        self,
        params: ControlParams,
        context: ExecutionContext
    ) -> Result[dict]:
        """
        执行浏览器控制操作

        Args:
            params: 控制参数
            context: 执行上下文

        Returns:
            控制操作结果
        """
        try:
            # 根据操作类型分发到具体处理函数
            action_handlers = {
                "clear_cookies": self._handle_clear_cookies,
                "delete_cookies": self._handle_delete_cookies,
                "get_login_qrcode": self._handle_get_login_qrcode,
                "publish_content": self._handle_publish_content,
                "publish_video": self._handle_publish_video,
                "schedule_publish": self._handle_schedule_publish,
                "check_publish_status": self._handle_check_publish_status,
                "search": self._handle_search,
                "like_feed": self._handle_like_feed,
                "favorite_feed": self._handle_favorite_feed,
                "post_comment": self._handle_post_comment,
                "reply_comment": self._handle_reply_comment,
            }

            handler = action_handlers.get(params.action)
            if not handler:
                return self.fail(
                    f"不支持的操作类型: {params.action}",
                    recoverable=True,
                    details={"supported_actions": list(action_handlers.keys())}
                )

            return await handler(params.params, context)

        except Exception as e:
            return self.error_from_exception(e, recoverable=True)

    async def _handle_clear_cookies(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理清除 Cookie 操作"""
        domains = params.get("domains", [])

        # 使用 evaluate 工具执行 JavaScript 清除 Cookie
        from src.tools.browser.evaluate import EvaluateTool

        try:
            eval_tool = EvaluateTool()

            # 构建清除 Cookie 的 JavaScript 代码
            js_code = """
            (function() {
                const domains = arguments[0] || [];
                let deletedCount = 0;

                domains.forEach(domain => {
                    const cookies = document.cookie.split(';');
                    cookies.forEach(cookie => {
                        const eqPos = cookie.indexOf('=');
                        if (eqPos >= 0) {
                            const name = cookie.substring(0, eqPos).trim();
                            document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;domain=' + domain;
                            deletedCount++;
                        }
                    });
                });

                return { success: true, deletedCount: deletedCount };
            })
            """

            result = await eval_tool.execute(
                params=eval_tool._get_params_type()(
                    code=js_code,
                    args=domains
                ),
                context=context
            )

            if result.success:
                return self.ok({
                    "success": True,
                    "deleted_count": result.data.get("deletedCount", 0) if result.data else 0
                })
            else:
                return self.fail("清除 Cookie 失败")

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_delete_cookies(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理删除指定 Cookie 操作"""
        delete_all = params.get("delete_all", False)
        cookie_names = params.get("cookie_names", [])

        from src.tools.browser.evaluate import EvaluateTool
        import logging

        logger = logging.getLogger("xhs_delete_cookies")

        try:
            eval_tool = EvaluateTool()

            # 详细日志
            tab_id = context.tab_id if context else None
            logger.info(
                f"[_handle_delete_cookies] 开始删除 - "
                f"tab_id={tab_id}, delete_all={delete_all}, cookie_names={cookie_names}"
            )

            if delete_all:
                # 清除所有 Cookie
                js_code = """
                (function() {
                    const cookies = document.cookie.split(';');
                    const deletedNames = [];
                    cookies.forEach(cookie => {
                        const eqPos = cookie.indexOf('=');
                        if (eqPos >= 0) {
                            const name = cookie.substring(0, eqPos).trim();
                            document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
                            deletedNames.push(name);
                        }
                    });
                    return { success: true, deleted_count: deletedNames.length, deleted_names: deletedNames };
                })
                """
            else:
                # 删除指定名称的 Cookie
                js_code = f"""
                (function() {{
                    const names = {cookie_names};
                    const deletedNames = [];
                    names.forEach(name => {{
                        document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
                        deletedNames.push(name);
                    }});
                    return {{ success: true, deleted_count: deletedNames.length, deleted_names: deletedNames }};
                }})
                """

            result = await eval_tool.execute(
                params=eval_tool._get_params_type()(code=js_code),
                context=context
            )

            if result.success:
                return self.ok({
                    "success": True,
                    "deleted_count": result.data.get("deleted_count", 0) if result.data else 0,
                    "deleted_names": result.data.get("deleted_names", []) if result.data else []
                })
            else:
                return self.fail("删除 Cookie 失败")

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_get_login_qrcode(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理获取登录二维码操作"""
        from src.tools.browser.extract import ExtractTool
        from src.tools.browser.navigate import NavigateTool

        try:
            # 导航到登录页面
            nav_tool = NavigateTool()
            await nav_tool.execute(
                params=nav_tool._get_params_type()(
                    url="https://www.xiaohongshu.com"
                ),
                context=context
            )

            # 等待二维码加载
            from src.tools.browser.wait import WaitTool
            wait_tool = WaitTool()
            await wait_tool.execute(
                params=wait_tool._get_params_type()(
                    selector=".qrcode, .login-qrcode, [class*='qrcode']",
                    timeout=10000
                ),
                context=context
            )

            # 获取 client、tab_id 和 secret_key
            client = getattr(context, 'client', None)
            tab_id = getattr(context, 'tab_id', None)
            secret_key = getattr(context, 'secret_key', None)

            # 如果没有 tab_id，先获取活动标签页
            if not tab_id and client:
                tab_result = await client.execute_tool("browser_control", {
                    "action": "get_active_tab"
                }, timeout=10000)
                logger.debug(f"获取活动标签页: {tab_result}")
                if tab_result.get("success") and tab_result.get("data"):
                    tab_id = tab_result.get("data", {}).get("tabId")
                    logger.info(f"获取到活动标签页: tabId={tab_id}")

            # 如果仍然没有 tab_id 创建新标签页并导航到小红书登录页
            if not tab_id and client:
                logger.info("没有活动标签页，创建新标签页...")

                # 先创建标签页并导航
                nav_result = await client.execute_tool("chrome_navigate", {
                    "url": "https://www.xiaohongshu.com/?author=0000000000000000000000",
                    "newTab": True
                }, timeout=15000)
                logger.debug(f"创建标签页结果: {nav_result}")
                if nav_result.get("success") and nav_result.get("data"):
                    tab_id = nav_result.get("data", {}).get("tabId")
                    logger.info(f"创建新标签页成功: tabId={tab_id}")

                # 等待导航完成
                await asyncio.sleep(2)

                await asyncio.sleep(2)

            # 等待页面加载完成
            await asyncio.sleep(3)

            # 等待登录弹窗出现
            if client and tab_id:
                # 先获取页面 URL 确认位置
                url_result = await client.execute_tool("read_page_data", {
                    "path": "location.href",
                    "tabId": tab_id
                }, timeout=5000)
                logger.info(f"当前页面 URL: {url_result.get('data')}")

                # 等待登录弹窗加载
                await asyncio.sleep(2)

            # 提取二维码信息 - 使用正确的选择器
            qrcode_js = """
                (function() {
                    var pageInfo = { title: document.title, url: window.location.href };
                    
                    // 参考 check_login_status.py 的方式 - 逐个尝试选择器
                    var selectors_results = [];
                    
                    var selectors = [
                        "#app > div:nth-child(1) > div > div.login-container > div.left > div.code-area > div.qrcode.force-light > img",
                        "#app > div > div > div.login-container > div.left > div.code-area > div.qrcode > img",
                        ".qrcode.force-light img",
                        ".code-area .qrcode img",
                        "img.qrcode-img",
                        "[class*='qrcode'] img",
                        "[class*='login'] img"
                    ];
                    
                    for (var i = 0; i < selectors.length; i++) {
                        var el = document.querySelector(selectors[i]);
                        if (el) {
                            var src = el.src || el.getAttribute("src") || "";
                            if (src) {
                                return { 
                                    found: true, 
                                    selector: selectors[i],
                                    src: src.substring(0, 500),
                                    isBase64: src.indexOf("data:") === 0,
                                    pageInfo: pageInfo
                                };
                            }
                        }
                    }
                    
                    // 返回调试信息
                    var allImgs = document.querySelectorAll("img");
                    var imgInfos = [];
                    for (var j = 0; j < Math.min(allImgs.length, 10); j++) {
                        imgInfos.push({
                            src: (allImgs[j].src || allImgs[j].getAttribute("src") || "").substring(0, 100),
                            className: allImgs[j].className
                        });
                    }
                    
                    return { 
                        found: false, 
                        pageInfo: pageInfo, 
                        total_images: allImgs.length, 
                        all_images: imgInfos 
                    };
                })()
            """

            if client and tab_id:
                result = await client.execute_tool("read_page_data", {
                    "path": qrcode_js,
                    "tabId": tab_id
                }, timeout=15000)
            elif client:
                # 尝试不指定 tab_id
                result = await client.execute_tool("read_page_data", {
                    "path": qrcode_js
                }, timeout=15000)
            else:
                logger.error("无法获取 client")
                result = {"success": False, "error": "no_client"}

            # 重试逻辑：如果第一次没找到，等一会再试
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries and (not result.get("success") or not result.get("data")):
                retry_count += 1
                logger.info(f"二维码提取重试 {retry_count}/{max_retries}")
                await asyncio.sleep(2)

                if client and tab_id:
                    result = await client.execute_tool("read_page_data", {
                        "path": qrcode_js,
                        "tabId": tab_id
                    }, timeout=15000)
                elif client:
                    result = await client.execute_tool("read_page_data", {
                        "path": qrcode_js
                    }, timeout=15000)

            logger.info(f"二维码提取结果: success={result.get('success')}, data={result.get('data')}, raw_data_type={type(result.get('data'))}, error={result.get('error')}")

            # 调试：打印返回数据的详细内容
            if result.get("data"):
                import json
                try:
                    logger.info(f"二维码数据详情: {json.dumps(result.get('data'), ensure_ascii=False)[:500]}")
                except:
                    logger.info(f"二维码数据详情: {result.get('data')}")

            import time
            expire_timestamp = int(time.time()) + 300  # 5分钟后过期

            if result.get("success") and result.get("data"):
                qrcode_url = None
                data = result.get("data")

                # 处理字符串类型的返回值（可能是 JSON 字符串）
                if isinstance(data, str):
                    try:
                        import json
                        data = json.loads(data)
                        logger.info(f"解析 JSON 字符串成功: {type(data)}")
                    except:
                        logger.warning(f"无法解析字符串为 JSON: {data[:100] if len(str(data)) > 100 else data}")
                        # 如果不是 JSON，可能是 base64 直接返回
                        if data.startswith("data:") or "base64" in data.lower():
                            qrcode_url = data

                # 处理字典类型 - 支持新的 found/src 格式
                if isinstance(data, dict):
                    # 新的返回格式
                    if data.get("found") is True:
                        qrcode_url = data.get("src")
                        logger.info(f"找到二维码，选择器: {data.get('selector')}, isBase64: {data.get('isBase64')}")
                    else:
                        # 旧的返回格式或其他
                        qrcode_url = data.get("src") or data.get("dataUrl") or data.get("qrcode_image", {}).get("src")
                        is_base64 = data.get("isBase64")

                logger.info(f"获取到二维码 URL: {qrcode_url}")
                return self.ok({
                    "qrcode_url": qrcode_url,
                    "qrcode_data": None,
                    "expire_time": expire_timestamp
                })

            # 如果无法提取，直接返回成功，让前端处理
            logger.warning("无法提取二维码元素，返回手动提示")
            return self.ok({
                "qrcode_url": None,
                "qrcode_data": None,
                "expire_time": expire_timestamp,
                "message": "请手动扫描页面上的二维码"
            })

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_publish_content(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理发布图文笔记操作"""
        from src.tools.browser.fill import FillTool
        from src.tools.browser.click import ClickTool
        from src.tools.browser.wait import WaitTool

        try:
            title = params.get("title", "")
            content = params.get("content", "")
            images = params.get("images", [])
            topic_tags = params.get("topic_tags", [])

            # 填写标题
            fill_tool = FillTool()
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".title-input, [contenteditable='true'], [data-testid='title-input']",
                    value=title
                ),
                context=context
            )

            # 填写内容
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".content-area, [contenteditable='true'], [data-testid='content-area']",
                    value=content + (" " + " ".join(f"#{t}#" for t in topic_tags) if topic_tags else "")
                ),
                context=context
            )

            # 点击发布按钮
            click_tool = ClickTool()
            await click_tool.execute(
                params=click_tool._get_params_type()(
                    selector=".publish-btn, .publish-button, [data-testid='publish-button']",
                    timeout=10000
                ),
                context=context
            )

            # 等待发布完成
            await asyncio.sleep(3)

            return self.ok({
                "success": True,
                "note_id": None,
                "url": None,
                "message": "发布请求已提交，请检查发布状态"
            })

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_publish_video(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理发布视频笔记操作"""
        from src.tools.browser.fill import FillTool
        from src.tools.browser.click import ClickTool
        from src.tools.browser.wait import WaitTool

        try:
            title = params.get("title", "")
            content = params.get("content", "")
            video_path = params.get("video_path", "")
            cover_image = params.get("cover_image")
            topic_tags = params.get("topic_tags", [])

            # 填写标题
            fill_tool = FillTool()
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".title-input, [contenteditable='true'], [data-testid='title-input']",
                    value=title
                ),
                context=context
            )

            # 填写内容
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".content-area, [contenteditable='true'], [data-testid='content-area']",
                    value=content + (" " + " ".join(f"#{t}#" for t in topic_tags) if topic_tags else "")
                ),
                context=context
            )

            # 点击发布按钮
            click_tool = ClickTool()
            await click_tool.execute(
                params=click_tool._get_params_type()(
                    selector=".publish-btn, .publish-button, [data-testid='publish-button']",
                    timeout=10000
                ),
                context=context
            )

            # 等待发布完成
            await asyncio.sleep(3)

            return self.ok({
                "success": True,
                "note_id": None,
                "url": None,
                "message": "视频发布请求已提交"
            })

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_schedule_publish(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理定时发布操作"""
        # 定时发布功能通常需要后端支持，这里返回提示信息
        from src.tools.browser.fill import FillTool
        from src.tools.browser.click import ClickTool

        try:
            title = params.get("title", "")
            content = params.get("content", "")
            schedule_time = params.get("schedule_time", "")

            # 填写标题和内容
            fill_tool = FillTool()
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".title-input, [contenteditable='true']",
                    value=title
                ),
                context=context
            )

            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".content-area, [contenteditable='true']",
                    value=content
                ),
                context=context
            )

            # 定时发布提示
            return self.ok({
                "success": True,
                "task_id": None,
                "scheduled_time": schedule_time,
                "message": f"定时发布已设置，时间: {schedule_time}（注意：定时发布需要后端支持）"
            })

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_check_publish_status(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理检查发布状态操作"""
        note_id = params.get("note_id")

        try:
            # 导航到笔记详情页
            from src.tools.browser.navigate import NavigateTool

            if note_id:
                nav_tool = NavigateTool()
                await nav_tool.execute(
                    params=nav_tool._get_params_type()(
                        url=f"https://www.xiaohongshu.com/explore/{note_id}"
                    ),
                    context=context
                )

            # 提取状态信息
            from src.tools.browser.extract import ExtractTool
            from src.tools.browser.evaluate import EvaluateTool

            eval_tool = EvaluateTool()

            # 尝试获取页面状态
            js_code = """
            (function() {
                const publishBtn = document.querySelector('.publish-btn, .publish-button');
                const statusText = document.querySelector('[class*="status"], [class*="publish"]');

                if (publishBtn) {
                    const text = publishBtn.textContent || publishBtn.innerText;
                    if (text.includes('发布')) {
                        return { status: 'draft', message: '草稿状态' };
                    }
                }

                return { status: 'unknown', message: '状态未知' };
            })
            """

            result = await eval_tool.execute(
                params=eval_tool._get_params_type()(code=js_code),
                context=context
            )

            if result.success and result.data:
                return self.ok({
                    "note_id": note_id,
                    "status": result.data.get("status", "unknown"),
                    "publish_time": None,
                    "views": 0,
                    "likes": 0
                })

            return self.ok({
                "note_id": note_id,
                "status": "unknown",
                "publish_time": None,
                "views": 0,
                "likes": 0,
                "message": "无法获取发布状态"
            })

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_search(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理搜索操作"""
        from src.tools.browser.fill import FillTool
        from src.tools.browser.click import ClickTool
        from src.tools.browser.wait import WaitTool

        try:
            keyword = params.get("keyword", "")
            search_type = params.get("search_type", "notes")
            max_items = params.get("max_items", 20)

            # 导航到搜索页
            from src.tools.browser.navigate import NavigateTool
            nav_tool = NavigateTool()
            await nav_tool.execute(
                params=nav_tool._get_params_type()(
                    url=f"https://www.xiaohongshu.com/search/{keyword}"
                ),
                context=context
            )

            # 等待搜索结果
            await asyncio.sleep(2)

            # 提取搜索结果
            from src.tools.browser.extract import ExtractTool
            from src.tools.browser.evaluate import EvaluateTool

            eval_tool = EvaluateTool()
            js_code = """
            (function(maxItems) {
                const items = [];
                const cards = document.querySelectorAll('.feed-card, .note-item, [class*="note-card"]');

                cards.slice(0, maxItems).forEach(card => {
                    const title = card.querySelector('.title, [class*="title"]')?.textContent;
                    const author = card.querySelector('.author, [class*="author"]')?.textContent;
                    const likes = card.querySelector('[class*="like"]')?.textContent || '0';

                    items.push({
                        title: title,
                        author: author,
                        likes: parseInt(likes) || 0
                    });
                });

                return { items: items, total_count: cards.length };
            })
            """

            result = await eval_tool.execute(
                params=eval_tool._get_params_type()(code=js_code, args=[max_items]),
                context=context
            )

            if result.success and result.data:
                return self.ok({
                    "items": result.data.get("items", []),
                    "keyword": keyword,
                    "search_type": search_type,
                    "total_count": result.data.get("total_count", 0)
                })

            return self.ok({
                "items": [],
                "keyword": keyword,
                "search_type": search_type,
                "total_count": 0,
                "message": "未找到搜索结果"
            })

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_like_feed(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理点赞操作"""
        from src.tools.browser.click import ClickTool
        from src.tools.browser.evaluate import EvaluateTool

        try:
            note_id = params.get("note_id", "")
            action_type = params.get("action_type", "like")

            # 使用 JavaScript 执行点赞
            eval_tool = EvaluateTool()
            js_code = f"""
            (function() {{
                // 查找笔记元素并点击点赞按钮
                const likeButtons = document.querySelectorAll('[class*="like"], .like-btn');
                for (const btn of likeButtons) {{
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {{
                        btn.click();
                        return {{ success: true, action: '{action_type}' }};
                    }}
                }}
                return {{ success: false, error: '未找到点赞按钮' }};
            }})
            """

            result = await eval_tool.execute(
                params=eval_tool._get_params_type()(code=js_code),
                context=context
            )

            if result.success:
                return self.ok({
                    "success": True,
                    "note_id": note_id,
                    "action": action_type
                })

            return self.fail("点赞失败")

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_favorite_feed(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理收藏操作"""
        from src.tools.browser.evaluate import EvaluateTool

        try:
            note_id = params.get("note_id", "")
            action_type = params.get("action_type", "favorite")
            folder_name = params.get("folder_name")

            eval_tool = EvaluateTool()
            js_code = """
            (function() {
                // 查找收藏按钮
                const collectButtons = document.querySelectorAll('[class*="collect"], .collect-btn, [class*="save"]');

                for (const btn of collectButtons) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        btn.click();
                        return { success: true, action: 'favorite' };
                    }
                }

                return { success: false, error: '未找到收藏按钮' };
            })
            """

            result = await eval_tool.execute(
                params=eval_tool._get_params_type()(code=js_code),
                context=context
            )

            if result.success:
                return self.ok({
                    "success": True,
                    "note_id": note_id,
                    "action": action_type,
                    "folder_name": folder_name
                })

            return self.fail("收藏失败")

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_post_comment(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理发表评论操作"""
        from src.tools.browser.fill import FillTool
        from src.tools.browser.click import ClickTool

        try:
            note_id = params.get("note_id", "")
            content = params.get("content", "")
            at_users = params.get("at_users", [])

            # 构建评论内容
            comment_content = content
            if at_users:
                at_text = " ".join(f"@{user}" for user in at_users)
                comment_content = f"{at_text} {content}"

            # 找到评论输入框并填写
            fill_tool = FillTool()
            result = await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".comment-input, [contenteditable='true'], [data-testid='comment-input']",
                    value=comment_content
                ),
                context=context
            )

            if not result.success:
                return self.fail("无法找到评论输入框")

            # 点击发送按钮
            click_tool = ClickTool()
            await click_tool.execute(
                params=click_tool._get_params_type()(
                    selector=".comment-submit, .send-comment, [data-testid='comment-submit']",
                    timeout=5000
                ),
                context=context
            )

            await asyncio.sleep(1)

            return self.ok({
                "success": True,
                "comment_id": None,
                "content": content
            })

        except Exception as e:
            return self.error_from_exception(e)

    async def _handle_reply_comment(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> Result[dict]:
        """处理回复评论操作"""
        from src.tools.browser.fill import FillTool
        from src.tools.browser.click import ClickTool

        try:
            comment_id = params.get("comment_id", "")
            content = params.get("content", "")

            # 找到评论输入框并填写回复
            fill_tool = FillTool()
            result = await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".reply-input, [contenteditable='true'], [data-testid='reply-input']",
                    value=content
                ),
                context=context
            )

            if not result.success:
                return self.fail("无法找到回复输入框")

            # 点击发送回复
            click_tool = ClickTool()
            await click_tool.execute(
                params=click_tool._get_params_type()(
                    selector=".reply-submit, .send-reply, [data-testid='reply-submit']",
                    timeout=5000
                ),
                context=context
            )

            await asyncio.sleep(1)

            return self.ok({
                "success": True,
                "reply_id": None,
                "comment_id": comment_id,
                "content": content
            })

        except Exception as e:
            return self.error_from_exception(e)


# ========== 便捷函数 ==========

async def browser_control(
    action: str,
    params: Dict[str, Any] = None,
    context: ExecutionContext = None
) -> Result[dict]:
    """
    执行浏览器控制操作

    Args:
        action: 控制操作类型
        params: 操作参数
        context: 执行上下文

    Returns:
        控制操作结果
    """
    tool = ControlTool()
    control_params = ControlParams(action=action, params=params or {})
    return await tool.execute(control_params, context or ExecutionContext())


async def clear_cookies(
    domains: List[str] = None,
    context: ExecutionContext = None
) -> Result[dict]:
    """清除 Cookie"""
    return await browser_control(
        action="clear_cookies",
        params={"domains": domains or []},
        context=context
    )


async def delete_cookies(
    cookie_names: List[str] = None,
    delete_all: bool = False,
    context: ExecutionContext = None
) -> Result[dict]:
    """删除指定 Cookie"""
    return await browser_control(
        action="delete_cookies",
        params={
            "cookie_names": cookie_names or [],
            "delete_all": delete_all
        },
        context=context
    )


async def get_login_qrcode(
    context: ExecutionContext = None
) -> Result[dict]:
    """获取登录二维码"""
    return await browser_control(
        action="get_login_qrcode",
        params={},
        context=context
    )


async def publish_content(
    title: str,
    content: str,
    images: List[str] = None,
    topic_tags: List[str] = None,
    context: ExecutionContext = None
) -> Result[dict]:
    """发布图文笔记"""
    return await browser_control(
        action="publish_content",
        params={
            "title": title,
            "content": content,
            "images": images or [],
            "topic_tags": topic_tags or []
        },
        context=context
    )


async def publish_video(
    title: str,
    content: str,
    video_path: str,
    cover_image: str = None,
    topic_tags: List[str] = None,
    context: ExecutionContext = None
) -> Result[dict]:
    """发布视频笔记"""
    return await browser_control(
        action="publish_video",
        params={
            "title": title,
            "content": content,
            "video_path": video_path,
            "cover_image": cover_image,
            "topic_tags": topic_tags or []
        },
        context=context
    )


async def search(
    keyword: str,
    search_type: str = "notes",
    max_items: int = 20,
    context: ExecutionContext = None
) -> Result[dict]:
    """搜索内容"""
    return await browser_control(
        action="search",
        params={
            "keyword": keyword,
            "search_type": search_type,
            "max_items": max_items
        },
        context=context
    )


async def like_feed(
    note_id: str,
    action: str = "like",
    context: ExecutionContext = None
) -> Result[dict]:
    """点赞笔记"""
    return await browser_control(
        action="like_feed",
        params={
            "note_id": note_id,
            "action_type": action
        },
        context=context
    )


async def favorite_feed(
    note_id: str,
    action: str = "favorite",
    folder_name: str = None,
    context: ExecutionContext = None
) -> Result[dict]:
    """收藏笔记"""
    return await browser_control(
        action="favorite_feed",
        params={
            "note_id": note_id,
            "action_type": action,
            "folder_name": folder_name
        },
        context=context
    )


async def post_comment(
    note_id: str,
    content: str,
    at_users: List[str] = None,
    context: ExecutionContext = None
) -> Result[dict]:
    """发表评论"""
    return await browser_control(
        action="post_comment",
        params={
            "note_id": note_id,
            "content": content,
            "at_users": at_users or []
        },
        context=context
    )


__all__ = [
    "ControlTool",
    "ControlParams",
    # 便捷函数
    "browser_control",
    "clear_cookies",
    "delete_cookies",
    "get_login_qrcode",
    "publish_content",
    "publish_video",
    "search",
    "like_feed",
    "favorite_feed",
    "post_comment",
]
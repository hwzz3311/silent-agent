"""
闲鱼发布商品工具

实现 xianyu_publish_item 工具，发布商品到闲鱼。
"""

import re
import asyncio
import os
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business import business_tool
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.sites.xianyu.adapters import XianyuSite
from .params import XYPublishItemParams
from .result import XYPublishItemResult


@business_tool(name="xianyu_publish_item", site_type=XianyuSite, operation_category="publish")
class PublishItemTool(BusinessTool[XYPublishItemParams]):
    """
    发布闲鱼商品

    支持发布带图片的商品到闲鱼。

    Usage:
        tool = PublishItemTool()
        result = await tool.execute(
            params=XYPublishItemParams(
                price="88",
                description="这是测试商品",
                image=["/path/to/image1.jpg"]
            ),
            context=context
        )

        if result.success:
            print(f"发布成功，商品ID: {result.data.item_id}")
    """

    name = "xianyu_publish_item"
    description = "发布商品到闲鱼，支持价格、描述、图片和分类"
    version = "1.0.0"
    category = "xianyu"
    operation_category = "publish"
    required_login = True

    # 直接模式类属性
    target_site_domain = "goofish.com"
    default_navigate_url = "https://www.goofish.com/publish"

    @log_operation("xianyu_publish_item")
    async def _execute_core(
        self,
        params: XYPublishItemParams,
        context: ExecutionContext,
    ) -> Any:
        """
        核心执行逻辑

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            XYPublishItemResult: 发布结果
        """
        import logging

        logger = logging.getLogger(f"business_tool.{self.name}")

        # 使用 context.client（依赖注入）
        client = context.client
        if not client:
            return XYPublishItemResult(
                success=False,
                message="无法获取浏览器客户端，请确保通过 API 调用"
            )

        # 使用 ensure_site_tab 获取标签页
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url=self.default_navigate_url,
            params_tab_id=params.tab_id
        )

        if not tab_id:
            return XYPublishItemResult(
                success=False,
                message="无法获取标签页"
            )

        try:
            # 辅助工具
            from src.tools.browser.fill import FillTool
            from src.tools.browser.click import ClickTool
            from src.tools.browser.evaluate import EvaluateTool
            from src.tools.browser.navigate import GetUrlTool

            fill_tool = FillTool()
            click_tool = ClickTool()
            eval_tool = EvaluateTool()

            # 1. 导航到发布页面
            await client.execute_tool(
                "chrome_navigate",
                {"url": "https://www.goofish.com/publish", "newTab": False},
                timeout=15000
            )
            await asyncio.sleep(2)

            # 2. 填写价格
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector=".ant-input",
                    value=params.price,
                    tab_id=tab_id
                ),
                context=context
            )
            print(f"[xianyu_publish] 价格: {params.price}")

            # 3. 填写描述
            await fill_tool.execute(
                params=fill_tool._get_params_type()(
                    selector="div[class^='editor--']",
                    value=params.description,
                    tab_id=tab_id
                ),
                context=context
            )
            print(f"[xianyu_publish] 描述: {params.description}")

            # 4. 上传图片
            if params.images:
                for idx, image_path in enumerate(params.images[:9]):  # 最多9张
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
                        from src.tools.browser.evaluate import EvaluateParams

                        await eval_tool.execute(
                            params=EvaluateParams(code=upload_script, args=[], tab_id=tab_id),
                            context=context
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
            from src.tools.browser.evaluate import EvaluateParams

            # 遍历分类直到找到支持的
            for i in range(params.category_index, 10):
                # 点击分类下拉框
                await click_tool.execute(
                    params=click_tool._get_params_type()(
                        selector="div.ant-select-selector",
                        timeout=5000,
                        tab_id=tab_id
                    ),
                    context=context
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
                    params=EvaluateParams(code=select_script, args=[], tab_id=tab_id),
                    context=context
                )
                await asyncio.sleep(0.5)

                # 检查是否还有不支持的警告
                result = await eval_tool.execute(
                    params=EvaluateParams(code=check_unsupported_script, args=[], tab_id=tab_id),
                    context=context
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
                params=EvaluateParams(code=publish_script, args=[], tab_id=tab_id),
                context=context
            )
            print("[xianyu_publish] 已点击发布按钮")

            # 等待发布完成
            await asyncio.sleep(3)

            # 7. 验证发布成功
            # 获取当前 URL 检查是否跳转到商品详情页
            get_url_tool = GetUrlTool()
            url_result = await get_url_tool.execute(
                params=get_url_tool._get_params_type()(tab_id=tab_id),
                context=context
            )
            current_url = url_result.data.get("url", "") if isinstance(url_result.data, dict) else ""

            print(f"[xianyu_publish] 当前 URL: {current_url}")

            # 检查 URL 是否包含 /item?id= (发布成功标志)
            if "/item?id=" in current_url:
                match = re.search(r'id=(\d+)', current_url)
                item_id = match.group(1) if match else None
                print(f"[xianyu_publish] 发布成功！商品ID: {item_id}")
                return XYPublishItemResult(
                    success=True,
                    item_id=item_id,
                    url=current_url,
                    message=self._get_publish_message({"item_id": item_id, "url": current_url})
                )
            else:
                print("[xianyu_publish] 发布结果未明，请检查截图")
                return XYPublishItemResult(
                    success=True,
                    item_id=None,
                    url=current_url,
                    message=self._get_publish_message({"item_id": None, "url": current_url})
                )

        except Exception as e:
            print(f"[xianyu_publish] 发布失败: {e}")
            return XYPublishItemResult(
                success=False,
                message=f"发布失败: {e}"
            )

    def _get_publish_message(self, result_data: dict) -> str:
        """生成发布结果消息"""
        if result_data.get("item_id"):
            return f"发布成功，商品ID: {result_data['item_id']}"
        else:
            return "发布成功"

# 便捷函数
async def publish_item(
    price: str,
    description: str,
    images: list = None,
    category_index: int = 3,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XYPublishItemResult:
    """
    便捷的发布商品函数

    Args:
        price: 商品价格
        description: 商品描述
        images: 图片路径列表
        category_index: 分类索引
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XYPublishItemResult: 发布结果
    """
    tool = PublishItemTool()
    params = XYPublishItemParams(
        price=price,
        description=description,
        images=images,
        category_index=category_index,
        tab_id=tab_id
    )
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XYPublishItemResult(
            success=False,
            message=f"发布失败: {result.error}"
        )


__all__ = [
    "PublishItemTool",
    "publish_item",
    "XYPublishItemParams",
    "XYPublishItemResult",
]
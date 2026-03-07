"""
闲鱼搜索商品工具

实现 xianyu_search_item 工具，在闲鱼搜索商品并获取搜索结果。
"""

import asyncio
from typing import Any, List

from src.tools.base import ExecutionContext
from src.tools.domain import business_tool
from src.tools.domain.base import BusinessTool
from src.tools.domain.logging import log_operation
from src.tools.sites.xianyu.adapters import XianyuSite
from .types import XYSearchItemParams, XYSearchItemResult, XYSearchItem


@business_tool(name="xianyu_search_item", site_type=XianyuSite, param_type=XYSearchItemParams, operation_category="browse")
class SearchItemTool(BusinessTool):
    """
    闲鱼搜索商品

    在闲鱼平台搜索关键词并获取搜索结果，支持翻页。

    Usage:
        tool = SearchItemTool()
        result = await tool.execute(
            params=XYSearchItemParams(
                keyword="爱奇艺",
                pages=2,
                items_per_page=30
            ),
            context=context
        )

        if result.success:
            print(f"获取 {result.data.total_items} 个商品")
            for item in result.data.results:
                print(f"{item.index}. {item.title} - {item.price}")
    """

    name = "xianyu_search_item"
    description = "在闲鱼搜索商品，支持翻页获取多个商品信息"
    version = "1.0.0"
    category = "xianyu"
    operation_category = "browse"
    required_login = False

    # 启用自动 Tab 管理
    target_site_domain = "goofish.com"
    default_navigate_url = "https://www.goofish.com"

    @log_operation("xianyu_search_item")
    async def _execute_core(
        self,
        params: XYSearchItemParams,
        context: ExecutionContext,
    ) -> Any:
        """
        核心执行逻辑

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            XYSearchItemResult: 搜索结果
        """
        import logging

        logger = logging.getLogger(f"business_tool.{self.name}")

        # 使用 context.client（依赖注入）
        client = context.client
        if not client:
            return XYSearchItemResult(
                success=False,
                message="无法获取浏览器客户端，请确保通过 API 调用"
            )

        # 使用 ensure_site_tab 获取标签页
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url=self.default_navigate_url,
            param_tab_id=params.tab_id
        )

        if not tab_id:
            return XYSearchItemResult(
                success=False,
                message="无法获取标签页"
            )

        try:
            # 辅助工具
            from src.tools.primitives.click import ClickTool
            from src.tools.primitives.fill import FillTool
            from src.tools.primitives.evaluate import EvaluateTool
            from src.tools.primitives.navigate import GetUrlTool

            click_tool = ClickTool()
            fill_tool = FillTool()
            eval_tool = EvaluateTool()
            get_url_tool = GetUrlTool()

            # 1. 获取当前页面 URL，检查是否在搜索页
            url_result = await get_url_tool.execute(
                params=get_url_tool._get_params_type()(tab_id=tab_id),
                context=context
            )
            current_url = url_result.data.get("url", "") if isinstance(url_result.data, dict) else ""
            logger.info(f"当前页面: {current_url}")

            # 2. 如果不在搜索页，执行搜索
            if "/search" not in current_url:
                logger.info(f"执行搜索: {params.keyword}")

                # 获取搜索框选择器（从适配器）
                site = self.get_site(context)
                search_input_selector = site.selectors.search_input
                search_button_selector = site.selectors.search_button

                # 点击搜索框
                await click_tool.execute(
                    params=click_tool._get_params_type()(
                        selector=search_input_selector,
                        tab_id=tab_id
                    ),
                    context=context
                )

                # 输入关键词
                await fill_tool.execute(
                    params=fill_tool._get_params_type()(
                        selector=search_input_selector,
                        value=params.keyword,
                        tab_id=tab_id
                    ),
                    context=context
                )

                # 点击搜索按钮
                await click_tool.execute(
                    params=click_tool._get_params_type()(
                        selector=search_button_selector,
                        tab_id=tab_id
                    ),
                    context=context
                )

                await asyncio.sleep(3)

            # 3. 循环获取多页数据
            all_results: List[XYSearchItem] = []

            for page in range(1, params.pages + 1):
                logger.info(f"获取第 {page} 页数据...")

                # 等待页面加载
                await asyncio.sleep(2)

                # 滚动加载更多内容
                await eval_tool.execute(
                    params=eval_tool._get_params_type()(
                        code="window.scrollBy(0, 1000)",
                        tab_id=tab_id
                    ),
                    context=context
                )
                await asyncio.sleep(1)

                # 提取商品信息 JS
                extract_script = f"""
                (function(){{
                    var links = document.querySelectorAll("a[href*='/item?']");
                    var items = [];
                    for(var i = 0; i < Math.min({params.items_perPage}, links.length); i++) {{
                        var link = links[i];
                        var parent = link.closest('a') || link.parentElement;
                        var id = link.href.match(/id=(\\d+)/)?.[1] || "";
                        var title = link.textContent?.trim() || "";
                        var html = parent?.innerHTML || "";

                        // 价格
                        var priceMatch = html.match(/¥(\\d+\\.?\\d*)/);
                        var price = priceMatch ? ("¥" + priceMatch[1]) : "";

                        // 想要数
                        var wantsMatch = html.match(/(\\d+)人想要/);
                        var wants = wantsMatch ? wantsMatch[1] : "0";

                        // 图片
                        var imgMatch = html.match(/src="([^"]+)"/);
                        var image = imgMatch ? imgMatch[1] : "";

                        // 卖家地区
                        var sellerMatch = html.match(/class="seller-text--[^"]+"[^>]*>([^<]+)/);
                        var seller = sellerMatch ? sellerMatch[1] : "";

                        // 信誉标签
                        var creditMatch = html.match(/class="gradient-image-text--[^"]+"[^>]*>([^<]+)/);
                        var sellerCredit = creditMatch ? creditMatch[1] : "";

                        // 标签
                        var tags = [];
                        var tagMatches = html.matchAll(/class="cpv--[^"]+"[^>]*>([^<]+)/g);
                        for (var m of tagMatches) tags.push(m[1]);

                        items.push({{
                            id: id,
                            title: title.substring(0, 150),
                            price: price,
                            wants: wants,
                            image: image,
                            seller: seller,
                            sellerCredit: sellerCredit,
                            tags: tags,
                            url: link.href
                        }});
                    }}
                    return items;
                }})()
                """

                eval_result = await eval_tool.execute(
                    params=eval_tool._get_params_type()(
                        code=extract_script,
                        tab_id=tab_id
                    ),
                    context=context
                )

                page_items = []
                if eval_result.success and eval_result.data:
                    raw_items = eval_result.data if isinstance(eval_result.data, list) else []
                    for idx, item in enumerate(raw_items):
                        page_items.append(XYSearchItem(
                            index=len(all_results) + idx + 1,
                            id=item.get("id", ""),
                            title=item.get("title", ""),
                            price=item.get("price", ""),
                            wants=item.get("wants", "0"),
                            image=item.get("image", ""),
                            seller=item.get("seller", ""),
                            seller_credit=item.get("sellerCredit", ""),
                            tags=item.get("tags", []),
                            url=item.get("url", "")
                        ))

                all_results.extend(page_items)
                logger.info(f"第 {page} 页获取 {len(page_items)} 个商品，累计 {len(all_results)} 个")

                # 翻页（如果不是最后一页）
                if page < params.pages:
                    logger.info(f"翻到第 {page + 1} 页...")

                    # 滚动到底部
                    await eval_tool.execute(
                        params=eval_tool._get_params_type()(
                            code="window.scrollTo(0, document.body.scrollHeight)",
                            tab_id=tab_id
                        ),
                        context=context
                    )
                    await asyncio.sleep(1)

                    # 查找下一页按钮
                    next_script = """
                    () => {
                        const btns = document.querySelectorAll('[class*="pagination"] a, [class*="page"] a, [class*="next"]');
                        const nextBtn = Array.from(btns).find(b => b.textContent?.includes('下一页') || b.textContent?.includes('>') || b.getAttribute('aria-label')?.includes('next'));
                        return nextBtn?.href || null;
                    }
                    """
                    next_result = await eval_tool.execute(
                        params=eval_tool._get_params_type()(
                            code=next_script,
                            tab_id=tab_id
                        ),
                        context=context
                    )

                    if next_result.success and next_result.data:
                        # 直接导航到下一页
                        await client.execute_tool(
                            "chrome_navigate",
                            {"url": next_result.data, "tabId": tab_id},
                            timeout=15000
                        )
                        await asyncio.sleep(3)
                    else:
                        # 尝试点击翻页按钮
                        click_next_script = """
                        () => {
                            const btns = Array.from(document.querySelectorAll('button, a')).filter(b => b.textContent?.includes('下一页') || b.getAttribute('aria-label')?.includes('next'));
                            if (btns[0]) { btns[0].click(); return 'clicked'; }
                            return 'not found';
                        }
                        """
                        click_result = await eval_tool.execute(
                            params=eval_tool._get_params_type()(
                                code=click_next_script,
                                tab_id=tab_id
                            ),
                            context=context
                        )
                        logger.info(f"翻页点击结果: {click_result.data}")
                        await asyncio.sleep(3)

            # 4. 返回结果
            return XYSearchItemResult(
                success=True,
                keyword=params.keyword,
                total_page=params.pages,
                total_items=len(all_results),
                results=all_results,
                message=f"搜索成功，共获取 {len(all_results)} 个商品"
            )

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return XYSearchItemResult(
                success=False,
                message=f"搜索失败: {e}"
            )


# 便捷函数
async def search_item(
    keyword: str,
    pages: int = 1,
    items_per_page: int = 30,
    tab_id: int = None,
    context: ExecutionContext = None
) -> XYSearchItemResult:
    """
    便捷的搜索商品函数

    Args:
        keyword: 搜索关键词
        pages: 获取页数
        items_per_page: 每页商品数
        tab_id: 标签页 ID
        context: 执行上下文

    Returns:
        XYSearchItemResult: 搜索结果
    """
    tool = SearchItemTool()
    params = XYSearchItemParams(
        keyword=keyword,
        pages=pages,
        items_per_page=items_per_page,
        tab_id=tab_id
    )
    ctx = context or ExecutionContext()

    result = await tool.execute(params, ctx)

    if result.success:
        return result.data
    else:
        return XYSearchItemResult(
            success=False,
            message=f"搜索失败: {result.error}"
        )


__all__ = [
    "SearchItemTool",
    "search_item",
    "XYSearchItemParams",
    "XYSearchItemResult",
]

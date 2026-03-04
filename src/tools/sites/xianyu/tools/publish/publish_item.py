"""
闲鱼发布商品工具

实现 xianyu_publish_item 工具，发布商品到闲鱼。
"""

from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xianyu.adapters import XianyuSite
from .params import XYPublishItemParams
from .result import XYPublishItemResult


class PublishItemTool(BusinessTool[XianyuSite, XYPublishItemParams]):
    """
    发布闲鱼商品

    支持发布带图片的商品到闲鱼。

    Usage:
        tool = PublishItemTool()
        result = await tool.execute(
            params=XYPublishItemParams(
                price="88",
                description="这是测试商品",
                images=["/path/to/image1.jpg"]
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
    site_type = XianyuSite
    required_login = True

    @log_operation("xianyu_publish_item")
    async def _execute_core(
        self,
        params: XYPublishItemParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑

        Args:
            params: 工具参数
            context: 执行上下文
            site: 网站适配器实例

        Returns:
            XYPublishItemResult: 发布结果
        """
        # 调用网站适配器的发布方法
        publish_result = await site.publish_item(
            context,
            price=params.price,
            description=params.description,
            images=params.images,
            category_index=params.category_index
        )

        if not publish_result.success:
            return XYPublishItemResult(
                success=False,
                message=f"发布失败: {publish_result.error}"
            )

        # 解析发布结果
        result_data = publish_result.data if isinstance(publish_result.data, dict) else {}

        return XYPublishItemResult(
            success=True,
            item_id=result_data.get("item_id"),
            url=result_data.get("url"),
            message=self._get_publish_message(result_data)
        )

    def _get_publish_message(self, result_data: dict) -> str:
        """生成发布结果消息"""
        if result_data.get("item_id"):
            return f"发布成功，商品ID: {result_data['item_id']}"
        else:
            return "发布成功"

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def publish_item(
    price: str,
    description: str,
    images: list = None,
    category_index: int = 3,
    context: ExecutionContext = None
) -> XYPublishItemResult:
    """
    便捷的发布商品函数

    Args:
        price: 商品价格
        description: 商品描述
        images: 图片路径列表
        category_index: 分类索引
        context: 执行上下文

    Returns:
        XYPublishItemResult: 发布结果
    """
    tool = PublishItemTool()
    params = XYPublishItemParams(
        price=price,
        description=description,
        images=images,
        category_index=category_index
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

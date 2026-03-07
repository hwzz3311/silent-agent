"""
闲鱼网站适配器

提供闲鱼 RPA 操作的统一接口。
"""

from .adapters import (
    XianyuSite,
    XianyuSiteConfig,
    XianyuSelectors,
    XianyuSliderSolver,
)

# 导入工具模块以触发 @business_tool 装饰器自动注册
from . import tools  # noqa: F401

__all__ = [
    "XianyuSite",
    "XianyuSiteConfig",
    "XianyuSelectors",
    "XianyuSliderSolver",
]

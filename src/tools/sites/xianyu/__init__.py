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

# 导入并注册工具
from .tools.publish import register as publish_register
from .tools.search import register as search_register

# 自动注册所有工具
__all_tools_registered = False

def ensure_tools_registered():
    """确保工具已注册（延迟注册）"""
    global __all_tools_registered
    if not __all_tools_registered:
        publish_register()
        search_register()
        __all_tools_registered = True

# 立即注册工具
ensure_tools_registered()

__all__ = [
    "XianyuSite",
    "XianyuSiteConfig",
    "XianyuSelectors",
    "XianyuSliderSolver",
    "ensure_tools_registered",
]

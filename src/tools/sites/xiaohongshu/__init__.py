"""
小红书 RPA 工具实现

使用业务抽象层框架实现的小红书特定 RPA 工具。

模块结构:
- adapters.py: 小红书网站适配器 (XiaohongshuSite)
- selectors.py: 小红书选择器定义
- tools/: 业务工具目录
    - login/: 登录相关工具
    - publish/: 发布相关工具
    - browse/: 浏览相关工具
    - interact/: 互动相关工具
- utils/: 底层工具（迁移自 src/tools/xhs/）
- publishers/: 发布流程编排器
"""

# 适配器
from .adapters import XiaohongshuSite, XHSSiteConfig, XHSSelectors

# 选择器
from .selectors import (
    XHSPageSelectors,
    XHSExtraSelectors,
    XHSSelectorSet,
    xhs_default_selectors,
    get_xhs_selectors,
)

# 底层工具（迁移自 xhs/）
from .utils import (
    ReadPageDataTool,
    InjectScriptTool,
    VideoDownloadTool,
    VideoChunkTransferTool,
    VideoUploadInterceptTool,
    UploadFileTool,
    SetFilesTool,
    get_video_store,
)

# 发布流程编排器
from .publishers import (
    XiaohongshuPublisher,
    PublishNoteParams,
    PublishVideoParams,
    PublishNoteResult,
    PublishVideoResult,
    publish_note,
    publish_video,
)


def register_xhs_tools():
    """
    注册所有小红书工具到全局注册表

    Usage:
        from tools.sites.xiaohongshu import register_xhs_tools
        register_xhs_tools()
    """
    from tools.business.registry import BusinessToolRegistry
    from .tools.login import register as login_register
    from .tools.publish import register as publish_register
    from .tools.browse import register as browse_register
    from .tools.interact import register as interact_register

    # 注册各类工具
    login_register()
    publish_register()
    browse_register()
    interact_register()

    return BusinessToolRegistry.get_by_site(XiaohongshuSite)


def get_xhs_tool_names() -> list:
    """获取所有小红书工具名称"""
    from tools.business.registry import BusinessToolRegistry

    tools = BusinessToolRegistry.get_by_site(XiaohongshuSite)
    return list(tools.keys())


__all__ = [
    # 适配器
    "XiaohongshuSite",
    "XHSSiteConfig",
    "XHSSelectors",
    # 选择器
    "XHSPageSelectors",
    "XHSExtraSelectors",
    "XHSSelectorSet",
    "xhs_default_selectors",
    "get_xhs_selectors",
    # 底层工具（迁移自 xhs/）
    "ReadPageDataTool",
    "InjectScriptTool",
    "VideoDownloadTool",
    "VideoChunkTransferTool",
    "VideoUploadInterceptTool",
    "UploadFileTool",
    "SetFilesTool",
    "get_video_store",
    # 发布流程编排器
    "XiaohongshuPublisher",
    "PublishNoteParams",
    "PublishVideoParams",
    "PublishNoteResult",
    "PublishVideoResult",
    "publish_note",
    "publish_video",
    # 注册函数
    "register_xhs_tools",
    "get_xhs_tool_names",
]

# 版本信息
__version__ = "1.0.0"
__description__ = "小红书 RPA 工具实现"
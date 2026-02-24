# Neurone 业务级 RPA 工具框架实现计划 (todos_v3)

> 参考: xiaohongshu-mcp Go MCP Server + 跨网站可复用架构
> 创建时间: 2026-02-13

---

## 一、整体架构设计

```
调用方 (Agent/API)
    ↓
src/api/routes/tools.py          # API 路由层
    ↓
src/tools/business/              # 业务工具抽象层 [可跨网站复用]
│   ├── __init__.py                  # 模块导出
│   ├── base.py                      # 抽象基类定义
│   ├── registry.py                  # 业务工具注册表
│   ├── errors.py                    # 统一错误处理
│   ├── logging.py                   # 业务日志装饰器
│   └── selectors/                   # 选择器管理
│       ├── base.py                  # 选择器基类
│       └── manager.py               # 选择器管理器
    ↓
src/tools/sites/                 # 网站特定实现 [小红书示例]
│   ├── __init__.py                  # 模块导出
│   ├── site_base.py                 # Site 抽象基类
│   ├── xiaohongshu/                 # 小红书实现
│   │   ├── __init__.py
│   │   ├── adapters.py              # 小红书适配器
│   │   ├── selectors.py             # 小红书选择器
│   │   └── tools/                   # 小红书业务工具
│   │       ├── __init__.py
│   │       ├── login/               # 登录工具
│   │       ├── publish/             # 发布工具
│   │       ├── browse/              # 浏览工具
│   │       └── interact/            # 互动工具
    ↓
src/tools/base.py                # 底层工具基类
    ↓
relay_client.NeuroneClient           # WebSocket 客户端
    ↓
Chrome Extension                     # 浏览器扩展
```

---

## 二、核心抽象框架 (Phase A) - 可跨网站复用

### A.1 抽象基类定义

#### A.1.1 Site 抽象基类
**文件**: `src/tools/business/site_base.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from tools.base import Tool, ExecutionContext

class SiteConfig(BaseModel):
    """网站配置"""
    site_name: str              # 网站标识
    base_url: str               # 基础 URL
    timeout: int = 30000        # 默认超时
    retry_count: int = 3        # 重试次数
    need_login: bool = True     # 是否需要登录

class SiteSelectorSet(BaseModel):
    """网站选择器集合"""
    # 通用选择器
    login_button: Optional[str] = None
    logout_button: Optional[str] = None
    user_avatar: Optional[str] = None
    username_display: Optional[str] = None

    # 弹窗/对话框
    modal_overlay: Optional[str] = None
    confirm_button: Optional[str] = None
    cancel_button: Optional[str] = None

class Site(ABC):
    """网站 RPA 操作的抽象基类"""

    config: SiteConfig
    selectors: SiteSelectorSet

    @abstractmethod
    async def navigate(self, page: str, context: ExecutionContext) -> bool:
        """导航到指定页面"""
        pass

    @abstractmethod
    async def check_login_status(self, context: ExecutionContext) -> Dict[str, Any]:
        """检查登录状态"""
        pass

    @abstractmethod
    async def extract_data(self, data_type: str, context: ExecutionContext) -> Any:
        """提取页面数据"""
        pass

    @abstractmethod
    async def wait_for_element(self, selector: str, timeout: int) -> bool:
        """等待元素出现"""
        pass

    def get_selector(self, key: str) -> Optional[str]:
        """获取选择器"""
        return getattr(self.selectors, key, None)
```

**任务分解**:
- A.1.1.1: 定义 SiteConfig 数据模型
- A.1.1.2: 定义 SiteSelectorSet 数据模型
- A.1.1.3: 定义 Site 抽象类和核心方法签名
- A.1.1.4: 添加类型注解和文档字符串

#### A.1.2 业务工具抽象基类
**文件**: `src/tools/business/base.py`

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel
from tools.base import Tool, ToolParameters, ExecutionContext
from .site_base import Site

SiteT = TypeVar('SiteT', bound=Site)
ParamsT = TypeVar('ParamsT', bound=ToolParameters)

class BusinessTool(Tool[ParamsT, Any], Generic[SiteT, ParamsT]):
    """
    业务级 RPA 工具的抽象基类

    特点:
    1. 泛型支持：支持不同的网站适配器
    2. 统一错误处理：继承统一错误处理机制
    3. 日志增强：自动记录操作步骤
    4. 选择器管理：使用网站选择器集合
    """

    # 子类必须覆盖
    site_type: type  # 对应的 Site 类型

    # 可选覆盖
    operation_category: str = "general"  # 操作分类

    async def execute(
        self,
        params: ParamsT,
        context: ExecutionContext
    ) -> Result[Any]:
        """
        统一的执行流程:
        1. 前置检查
        2. 获取网站适配器
        3. 执行操作
        4. 后置处理
        """
        pass

    def get_site(self, context: ExecutionContext) -> Site:
        """获取网站适配器实例"""
        pass

    async def _pre_execute(self, params: ParamsT, context: ExecutionContext) -> bool:
        """前置检查（可覆盖）"""
        pass

    async def _post_execute(self, result: Result, context: ExecutionContext) -> Result:
        """后置处理（可覆盖）"""
        pass
```

**任务分解**:
- A.1.2.1: 定义 BusinessTool 泛型基类
- A.1.2.2: 实现统一执行流程模板方法
- A.1.2.3: 添加网站适配器获取方法
- A.1.2.4: 实现默认的前置/后置处理

#### A.1.3 工具注册表
**文件**: `src/tools/business/registry.py`

```python
from typing import Dict, Type, Optional
from .base import BusinessTool, SiteT
from .site_base import Site

class BusinessToolRegistry:
    """
    业务工具注册表

    功能:
    1. 工具注册与注销
    2. 按类别查找工具
    3. 按网站类型查找工具
    4. 工具版本管理
    """

    _tools: Dict[str, BusinessTool] = {}
    _site_tools: Dict[type, Dict[str, BusinessTool]] = {}  # site_type -> tools
    _categories: Dict[str, set] = {}  # category -> tool_names

    @classmethod
    def register(cls, tool: BusinessTool) -> None:
        """注册业务工具"""
        pass

    @classmethod
    def get(cls, name: str) -> Optional[BusinessTool]:
        """获取工具"""
        pass

    @classmethod
    def get_by_site(cls, site_type: type) -> Dict[str, BusinessTool]:
        """获取指定网站的所有工具"""
        pass

    @classmethod
    def get_by_category(cls, category: str) -> Dict[str, BusinessTool]:
        """获取指定类别的所有工具"""
        pass

    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有工具"""
        pass
```

**任务分解**:
- A.1.3.1: 实现注册表核心功能
- A.1.3.2: 实现网站类型索引
- A.1.3.3: 实现类别索引
- A.1.3.4: 添加工具版本支持

#### A.1.4 统一错误处理
**文件**: `src/tools/business/errors.py`

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any

class BusinessErrorCode(str, Enum):
    """业务错误代码"""
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    PAGE_NOT_FOUND = "PAGE_NOT_FOUND"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    SITE_STRUCTURE_CHANGED = "SITE_STRUCTURE_CHANGED"
    RATE_LIMITED = "RATE_LIMITED"

class BusinessError(BaseModel):
    """业务错误"""
    code: BusinessErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    site_name: Optional[str] = None
    operation: Optional[str] = None
    selector: Optional[str] = None
    suggestion: Optional[str] = None  # 修复建议

class BusinessException(Exception):
    """业务异常"""

    def __init__(
        self,
        code: BusinessErrorCode,
        message: str,
        **kwargs
    ):
        self.code = code
        self.message = message
        self.details = kwargs

    @classmethod
    def login_required(cls, site_name: str = None) -> 'BusinessException':
        """需要登录"""
        pass

    @classmethod
    def element_not_found(
        cls,
        selector: str,
        operation: str,
        suggestion: str = None
    ) -> 'BusinessException':
        """元素未找到"""
        pass

    @classmethod
    def site_structure_changed(
        cls,
        site_name: str,
        operation: str,
        suggestion: str = "请更新选择器"
    ) -> 'BusinessException':
        """网站结构变化"""
        pass
```

**任务分解**:
- A.1.4.1: 定义错误代码枚举
- A.1.4.2: 定义 BusinessError 数据模型
- A.1.4.3: 定义 BusinessException 异常类
- A.1.4.4: 实现便捷工厂方法

#### A.1.5 业务日志装饰器
**文件**: `src/tools/business/logging.py`

```python
import functools
import logging
from typing import Callable, Any
from .errors import BusinessError

def log_operation(
    operation_name: str,
    logger: logging.Logger = None
) -> Callable:
    """
    业务操作日志装饰器

    功能:
    1. 自动记录操作开始/结束
    2. 记录操作参数（脱敏）
    3. 记录错误和堆栈
    4. 记录操作耗时
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            pass
        return wrapper
    return decorator

class BusinessLogger:
    """
    业务日志记录器

    功能:
    1. 结构化日志输出
    2. 自动包含站点和操作信息
    3. 错误上下文记录
    """

    def __init__(self, site_name: str, operation: str):
        self.site_name = site_name
        self.operation = operation

    def log_step(self, step: str, **kwargs) -> None:
        """记录步骤"""
        pass

    def log_error(self, error: Exception, **kwargs) -> None:
        """记录错误"""
        pass

    def log_result(self, success: bool, **kwargs) -> None:
        """记录结果"""
        pass
```

**任务分解**:
- A.1.5.1: 实现日志装饰器
- A.1.5.2: 实现 BusinessLogger 类
- A.1.5.3: 添加参数脱敏功能
- A.1.5.4: 集成到 BusinessTool 基类

#### A.1.6 选择器管理器
**文件**: `src/tools/business/selectors/manager.py`

```python
from typing import Dict, Optional, Any
from .base import Selector, SelectorType

class SelectorManager:
    """
    选择器管理器

    功能:
    1. 选择器版本管理
    2. 选择器自动降级
    3. 选择器缓存
    4. 选择器验证
    """

    def __init__(self, site_name: str):
        self.site_name = site_name
        self._selectors: Dict[str, Selector] = {}
        self._cache: Dict[str, str] = {}

    def register_selector(self, name: str, selector: Selector) -> None:
        """注册选择器"""
        pass

    def get_selector(
        self,
        name: str,
        fallback: bool = True
    ) -> Optional[str]:
        """获取选择器"""
        pass

    def validate_selector(self, selector: str) -> bool:
        """验证选择器有效性"""
        pass

    def record_success(self, selector: str) -> None:
        """记录选择器使用成功"""
        pass

    def record_failure(self, selector: str, error: Exception) -> None:
        """记录选择器使用失败"""
        pass

    def get_fallback_selector(self, name: str) -> Optional[str]:
        """获取备用选择器"""
        pass
```

**任务分解**:
- A.1.6.1: 定义 Selector 数据模型
- A.1.6.2: 实现选择器注册和获取
- A.1.6.3: 实现选择器验证
- A.1.6.4: 实现选择器自动降级

---

## 三、网站特定实现 (Phase B) - 小红书示例

### B.1 小红书适配器

#### B.1.1 小红书 Site 适配器
**文件**: `src/tools/sites/xiaohongshu/adapters.py`

```python
from typing import Any, Dict, Optional
from pydantic import Field
from tools.base import ExecutionContext

from .selectors import XHSSelectors
from ...business.site_base import Site, SiteConfig, SiteSelectorSet
from ...business.errors import BusinessException

class XHSSiteConfig(SiteConfig):
    """小红书配置"""
    site_name: str = "xiaohongshu"
    base_url: str = "https://www.xiaohongshu.com"
    timeout: int = 30000
    retry_count: int = 3
    need_login: bool = True

class XHSSelectors(SiteSelectorSet):
    """小红书选择器集合"""

    # 登录相关
    login_button: str = ".login-btn, [data-testid='login-btn']"
    user_avatar: str = ".user-avatar, [data-testid='user-avatar']"
    username_display: str = ".user-name, [data-testid='username']"

    # 弹窗
    modal_overlay: str = ".modal-overlay, .overlay"
    confirm_button: str = ".confirm-btn, [data-testid='confirm']"
    cancel_button: str = ".cancel-btn, [data-testid='cancel']"

class XiaohongshuSite(Site):
    """
    小红书网站 RPA 操作适配器

    实现 Site 抽象基类的所有抽象方法
    """

    config: XHSSiteConfig
    selectors: XHSSelectors

    async def navigate(self, page: str, context: ExecutionContext) -> bool:
        """
        导航到小红书页面

        页面类型:
        - home: 首页
        - login: 登录页
        - profile: 用户主页
        - feed: 笔记详情页
        - search: 搜索页
        """
        pass

    async def check_login_status(self, context: ExecutionContext) -> Dict[str, Any]:
        """检查登录状态"""
        pass

    async def extract_data(self, data_type: str, context: ExecutionContext) -> Any:
        """
        提取小红书页面数据

        data_type:
        - feed_list: 笔记列表
        - feed_detail: 笔记详情
        - user_profile: 用户主页
        - comments: 评论列表
        """
        pass

    async def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """等待元素出现"""
        pass
```

**任务分解**:
- B.1.1.1: 定义 XHSSiteConfig
- B.1.1.2: 定义 XHSSelectors 选择器集合
- B.1.1.3: 实现 XiaohongshuSite 导航方法
- B.1.1.4: 实现 XiaohongshuSite 登录检查方法
- B.1.1.5: 实现 XiaohongshuSite 数据提取方法

#### B.1.2 小红书选择器
**文件**: `src/tools/sites/xiaohongshu/selectors.py`

```python
from pydantic import BaseModel
from typing import Optional, Dict, List

class XHSPageSelectors(BaseModel):
    """小红书页面选择器"""

    # 通用分页
    next_page_button: str = ".next-btn, .load-more"
    infinite_scroll_container: str = ".feed-list, .infinite-scroll"

    # 首页
    feed_card: str = ".feed-card, [data-testid='feed-card']"
    feed_title: str = ".feed-title, [data-testid='feed-title']"
    feed_cover: str = ".feed-cover, [data-testid='feed-cover']"
    feed_author: str = ".feed-author, [data-testid='feed-author']"
    feed_likes: str = ".feed-likes, [data-testid='feed-likes']"
    feed_comments: str = ".feed-comments, [data-testid='feed-comments']"

    # 笔记详情页
    detail_container: str = ".note-detail, [data-testid='note-detail']"
    detail_title: str = ".note-title, [data-testid='note-title']"
    detail_content: str = ".note-content, [data-testid='note-content']"
    detail_images: List[str] = [".detail-image"]
    detail_likes: str = ".detail-likes"
    detail_collect: str = ".detail-collect"
    detail_comment_input: str = ".comment-input, [contenteditable='true']"
    detail_comment_submit: str = ".comment-submit"

    # 用户主页
    profile_container: str = ".user-profile, [data-testid='user-profile']"
    profile_avatar: str = ".profile-avatar"
    profile_name: str = ".profile-name"
    profile_followers: str = ".profile-followers"
    profile_following: str = ".profile-following"
    profile_likes: str = ".profile-likes"
    profile_notes: str = ".profile-notes"

    # 搜索页
    search_input: str = ".search-input, [data-testid='search-input']"
    search_button: str = ".search-btn, [data-testid='search-btn']"
    search_result: str = ".search-result, [data-testid='search-result']"

class XHSExtraSelectors(BaseModel):
    """小红书额外选择器（备用）"""
    feed_card_alternatives: List[str] = [
        "[data-testid='feed-card']",
        ".feed-item",
        ".note-item"
    ]

class XHSSelectorSet(BaseModel):
    """小红书完整选择器集合"""
    page: XHSPageSelectors = XHSPageSelectors()
    extra: XHSExtraSelectors = XHSExtraSelectors()
    fallbacks: Dict[str, List[str]] = {}

    def get_with_fallback(self, primary: str, fallback_key: str) -> str:
        """获取主选择器，失败时使用备用"""
        pass
```

**任务分解**:
- B.1.2.1: 定义页面选择器
- B.1.2.2: 定义备用选择器
- B.1.2.3: 实现选择器回退逻辑

---

## 四、基础设施工具 (Phase C)

### C.1 页面导航增强
**文件**: `src/tools/sites/xiaohongshu/navigation.py`

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from tools.base import ToolParameters, ExecutionContext

class SiteNavigationParams(ToolParameters):
    """页面导航参数"""
    page: str = Field(
        ...,
        description="页面类型: home|login|profile|feed|search"
    )
    page_id: Optional[str] = Field(
        None,
        description="页面ID (用户ID/笔记ID等)"
    )
    tab_id: Optional[int] = None

class XHSNavigateParams(SiteNavigationParams):
    """小红书导航参数"""
    # 小红书特定页面
    # home - 首页
    # login - 登录页
    # profile/{user_id} - 用户主页
    # feed/{note_id} - 笔记详情
    # search/{keyword} - 搜索页
    pass
```

### C.2 页面数据读取增强
**文件**: `src/tools/sites/xiaohongshu/data_extractor.py`

```python
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from tools.base import ToolParameters

class XHSExtractParams(ToolParameters):
    """小红书数据提取参数"""
    data_type: str = Field(
        ...,
        description="数据类型: feed_list|feed_detail|user_profile|comments|search_results"
    )
    selectors: Optional[Dict[str, str]] = None  # 自定义选择器
    max_items: int = Field(20, description="最大提取数量")

class XHSFeedItem(BaseModel):
    """小红书笔记项"""
    note_id: str
    xsec_token: str
    title: str
    cover_image: Optional[str] = None
    author: Optional[Dict[str, Any]] = None
    likes: int = 0
    comments: int = 0
    collect: int = 0

class XHSFeedListResult(BaseModel):
    """笔记列表结果"""
    items: List[XHSFeedItem]
    has_more: bool
    next_cursor: Optional[str] = None

class XHSUserProfileResult(BaseModel):
    """用户主页结果"""
    user_id: str
    nickname: str
    avatar: Optional[str] = None
    description: Optional[str] = None
    followers: int = 0
    following: int = 0
    likes: int = 0
    notes_count: int = 0
```

---

## 五、业务工具实现 (Phase D)

### D.1 登录工具模块

**目录**: `src/tools/sites/xiaohongshu/tools/login/`

| 工具名 | 文件 | 状态 |
|--------|------|------|
| `xhs_check_login_status` | `check_login_status.py` | ✅ 已完成 |
| `xhs_get_login_qrcode` | `get_login_qrcode.py` | ✅ 已完成 |
| `xhs_delete_cookies` | `delete_cookies.py` | ✅ 已完成 |
| `xhs_wait_login` | `wait_login.py` | ✅ 已完成 |

### D.2 发布工具模块

**目录**: `src/tools/sites/xiaohongshu/tools/publish/`

| 工具名 | 文件 | 状态 |
|--------|------|------|
| `xhs_publish_content` | `publish_content.py` | ✅ 已完成 |
| `xhs_publish_video` | `publish_video.py` | ✅ 已完成 |
| `xhs_schedule_publish` | `schedule_publish.py` | ✅ 已完成 |
| `xhs_check_publish_status` | `check_publish_status.py` | ✅ 已完成 |

### D.3 浏览工具模块

**目录**: `src/tools/sites/xiaohongshu/tools/browse/`

| 工具名 | 文件 | 状态 |
|--------|------|------|
| `xhs_list_feeds` | `list_feeds.py` | ✅ 已完成 |
| `xhs_search_feeds` | `search_feeds.py` | ✅ 已完成 |
| `xhs_get_feed_detail` | `get_feed_detail.py` | ✅ 已完成 |
| `xhs_user_profile` | `user_profile.py` | ✅ 已完成 |

### D.4 互动工具模块

**目录**: `src/tools/sites/xiaohongshu/tools/interact/`

| 工具名 | 文件 | 状态 |
|--------|------|------|
| `xhs_like_feed` | `like_feed.py` | ✅ 已完成 |
| `xhs_favorite_feed` | `favorite_feed.py` | ✅ 已完成 |
| `xhs_post_comment` | `post_comment.py` | ✅ 已完成 |
| `xhs_reply_comment` | `reply_comment.py` | ✅ 已完成 |

---

## 六、模块导出与注册 (Phase E)

### E.1 业务工具模块导出
**文件**: `src/tools/business/__init__.py`

```python
"""业务级 RPA 工具抽象层

提供跨网站可复用的抽象基类和工具。
"""

# 抽象基类
from .base import BusinessTool
from .site_base import Site, SiteConfig, SiteSelectorSet

# 注册表
from .registry import BusinessToolRegistry, business_registry

# 错误处理
from .errors import (
    BusinessError,
    BusinessErrorCode,
    BusinessException
)

# 日志
from .logging import BusinessLogger, log_operation

# 选择器管理
from .selectors import SelectorManager

__all__ = [
    # 抽象基类
    "BusinessTool",
    "Site",
    "SiteConfig",
    "SiteSelectorSet",
    # 注册表
    "BusinessToolRegistry",
    "business_registry",
    # 错误处理
    "BusinessError",
    "BusinessErrorCode",
    "BusinessException",
    # 日志
    "BusinessLogger",
    "log_operation",
    # 选择器管理
    "SelectorManager",
]
```

### E.2 小红书工具模块导出
**文件**: `src/tools/sites/xiaohongshu/__init__.py`

```python
"""小红书 RPA 工具实现

使用业务抽象层实现的小红书特定工具。
"""

from .adapters import XiaohongshuSite, XHSSiteConfig, XHSSelectors
from .tools import (
    login,
    publish,
    browse,
    interact,
)

def register_xhs_tools():
    """注册所有小红书工具"""
    pass

__all__ = [
    "XiaohongshuSite",
    "XHSSiteConfig",
    "XHSSelectors",
    "register_xhs_tools",
]
```

---

## 七、开发规范与指南 (Phase F)

### F.1 新网站适配指南
**文件**: `docs/website-adapter-guide.md`

```markdown
# 网站适配器开发指南

## 1. 创建网站适配器

### 1.1 创建目录结构
```
src/tools/sites/[site_name]/
├── __init__.py
├── adapters.py           # 网站适配器
├── selectors.py          # 选择器定义
└── tools/                # 业务工具
    ├── __init__.py
    ├── login/            # 登录工具
    ├── publish/          # 发布工具
    ├── browse/           # 浏览工具
    └── interact/         # 互动工具
```

### 1.2 实现适配器类
1. 继承 Site 抽象基类
2. 配置 SiteConfig
3. 定义选择器集合
4. 实现所有抽象方法

### 1.3 实现业务工具
1. 继承 BusinessTool 基类
2. 设置 site_type
3. 实现 execute 方法
```

### F.2 工具开发模板
**文件**: `templates/business_tool_template.py`

```python
"""工具名称

工具描述
"""

from typing import Any, Optional
from pydantic import Field

from tools.base import ToolParameters, ExecutionContext
from ..business.base import BusinessTool
from ..business.errors import BusinessException, BusinessErrorCode
from ..business.logging import log_operation

class ToolNameParams(ToolParameters):
    """工具参数"""
    param1: str = Field(..., description="参数1")
    param2: Optional[str] = Field(None, description="参数2")

class ToolNameResult(BaseModel):
    """工具返回结果"""
    success: bool
    data: Any = None
    message: str = ""

class ToolName(BusinessTool):
    """
    工具名称

    继承 BusinessTool，实现小红书[操作类型]功能。
    """

    name = "xhs_tool_name"
    description = "工具描述"
    category = "xiaohongshu"  # 操作分类
    version = "1.0.0"
    site_type = XiaohongshuSite  # 对应的网站类型

    @log_operation("xhs_tool_name")
    async def execute(
        self,
        params: ToolNameParams,
        context: ExecutionContext
    ) -> Result[ToolNameResult]:
        try:
            # 1. 前置检查
            if not await self._pre_execute(params, context):
                return self.fail("前置检查失败")

            # 2. 获取网站适配器
            site = self.get_site(context)

            # 3. 执行操作
            # ... 业务逻辑

            # 4. 返回结果
            return self.ok(ToolNameResult(
                success=True,
                data=...,
                message="操作成功"
            ))

        except BusinessException as e:
            return self.fail(e.message, details={"code": e.code})
        except Exception as e:
            return self.error_from_exception(e)
```

---

## 八、任务清单汇总

| 阶段 | 任务数 | 说明 | 状态 |
|------|--------|------|------|
| **Phase A** | 6 | 核心抽象框架（Site、BusinessTool、注册表、错误、日志、选择器） | ✅ 已完成 |
| **Phase B** | 5 | 小红书适配器（配置、选择器、适配器） | ✅ 已完成 |
| **Phase C** | 2 | 基础设施（导航、数据读取增强） | ✅ 已完成 |
| **Phase D** | 16 | 小红书业务工具实现（4模块×4工具） | ✅ 已完成 |
| **Phase E** | 2 | 模块导出与注册 | ✅ 已完成 |
| **Phase F** | 2 | 开发规范与模板（可选文档） | ⚠️ 可选 |
| **合计** | **33** | | |

## 九、工具完成统计

| 类别 | 计划 | 实际 | 状态 |
|------|------|------|------|
| 登录工具 | 4 | 4 | ✅ 完成 |
| 发布工具 | 4 | 4 | ✅ 完成 |
| 浏览工具 | 4 | 4 | ✅ 完成 |
| 互动工具 | 4 | 4 | ✅ 完成 |
| **总计** | **16** | **16** | **✅ 全部完成** |

## 十、已完成文件清单

### Phase A - 核心抽象框架
- [x] `src/tools/business/site_base.py` - Site 抽象基类
- [x] `src/tools/business/base.py` - BusinessTool 基类
- [x] `src/tools/business/registry.py` - 工具注册表
- [x] `src/tools/business/errors.py` - 统一错误处理
- [x] `src/tools/business/logging.py` - 业务日志
- [x] `src/tools/business/selectors/manager.py` - 选择器管理器
- [x] `src/tools/business/__init__.py` - 模块导出

### Phase B - 小红书适配器
- [x] `src/tools/sites/xiaohongshu/adapters.py` - 小红书适配器
- [x] `src/tools/sites/xiaohongshu/selectors.py` - 小红书选择器
- [x] `src/tools/sites/xiaohongshu/__init__.py` - 模块导出
- [x] `src/tools/sites/__init__.py` - 网站模块导出
- [x] `src/tools/sites/xiaohongshu/tools/login/__init__.py` - 登录工具结构
- [x] `src/tools/sites/xiaohongshu/tools/publish/__init__.py` - 发布工具结构
- [x] `src/tools/sites/xiaohongshu/tools/browse/__init__.py` - 浏览工具结构
- [x] `src/tools/sites/xiaohongshu/tools/interact/__init__.py` - 互动工具结构 |

---

## 十一、任务依赖关系

```
Phase A (核心框架)
    │
    ├──▶ Phase B (小红书适配器)
    │           │
    │           └──▶ Phase C (基础设施)
    │                   │
    │                   └──▶ Phase D (业务工具实现)
    │                           │
    │                           └──▶ Phase E (注册与导出)
    │                                   │
    │                                   └──▶ Phase F (文档)
    │
    └──▶ Phase F (文档)  # 可并行

详细依赖:
A.1 (Site基类) ──┬──> B.1 (小红书适配器)
    │            │
    ├──> A.2 ───┤
    │            │
    ├──> A.3 ───┤
    │            │
    ├──> A.4 ───┤
    │            │
    └──> A.6 ───┘

C.1, C.2 ───> D.1 ~ D.4
```

---

## 十二、实现优先级建议

### 已完成 ✅

所有阶段已完成实现！以下是完成状态：

| 优先级 | 阶段 | 状态 |
|--------|------|------|
| 1 | **A.1 (Site基类)** | ✅ 已完成 |
| 2 | **A.2 (BusinessTool)** | ✅ 已完成 |
| 3 | **A.3 (工具注册表)** | ✅ 已完成 |
| 4 | **B.1 (小红书适配器)** | ✅ 已完成 |
| 5 | **C.1-2 (基础设施)** | ✅ 已完成 |
| 6 | **D.1 (登录工具)** | ✅ 已完成（4/4） |
| 7 | **D.2 (发布工具)** | ✅ 已完成（4/4） |
| 8 | **D.3 (浏览工具)** | ✅ 已完成（4/4） |
| 9 | **D.4 (互动工具)** | ✅ 已完成（4/4） |
| 10 | **E (注册与导出)** | ✅ 已完成 |

### 可选扩展（Phase F 文档）

- 创建 `docs/website-adapter-guide.md` - 网站适配器开发指南
- 创建 `templates/business_tool_template.py` - 工具开发模板

---

## 十三、使用指南

### 注册所有小红书工具

```python
from src.tools.sites.xiaohongshu.tools.login import register as login_register
from src.tools.sites.xiaohongshu.tools.publish import register as publish_register
from src.tools.sites.xiaohongshu.tools.browse import register as browse_register
from src.tools.sites.xiaohongshu.tools.interact import register as interact_register

# 一键注册所有工具
total = 0
total += login_register()
total += publish_register()
total += browse_register()
total += interact_register()
print(f"注册了 {total} 个工具")
```

### 使用业务工具

```python
from src.tools.sites.xiaohongshu.tools.login import CheckLoginStatusTool
from src.tools.sites.xiaohongshu.tools.publish import PublishContentTool
from src.tools.sites.xiaohongshu.tools.interact import LikeFeedTool

# 获取已注册的 tool
from src.tools.business.registry import BusinessToolRegistry

tool = BusinessToolRegistry.get("xhs_check_login_status")
if tool:
    result = await tool.execute(params, context)
```

---

## 十四、代码示例

### 示例 1: 使用 BusinessTool 实现小红书登录检查

```python
# src/tools/sites/xiaohongshu/tools/login/check_login_status.py

from typing import Any, Dict, Optional
from pydantic import Field
from tools.base import ExecutionContext

from .....business.base import BusinessTool
from .....business.errors import BusinessException
from .....business.logging import log_operation
from ..adapters import XiaohongshuSite
from .params import XHSCheckLoginStatusParams
from .result import XHSCheckLoginStatusResult

class XHSCheckLoginStatusTool(BusinessTool[XiaohongshuSite, XHSCheckLoginStatusParams]):
    """
    检查小红书登录状态

    返回当前用户是否已登录，以及用户信息。
    """

    name = "xhs_check_login_status"
    description = "检查小红书登录状态，返回用户名等信息"
    category = "xiaohongshu"
    version = "1.0.0"
    site_type = XiaohongshuSite
    operation_category = "login"

    @log_operation("xhs_check_login_status")
    async def execute(
        self,
        params: XHSCheckLoginStatusParams,
        context: ExecutionContext
    ) -> Result[XHSCheckLoginStatusResult]:
        try:
            # 1. 获取小红书适配器
            site = self.get_site(context)

            # 2. 执行登录状态检查
            login_data = await site.check_login_status(context)

            # 3. 返回结果
            return self.ok(XHSCheckLoginStatusResult(
                success=True,
                is_logged_in=login_data.get("is_logged_in", False),
                username=login_data.get("username"),
                user_id=login_data.get("user_id"),
                avatar=login_data.get("avatar"),
                message="登录状态检查成功"
            ))

        except Exception as e:
            return self.error_from_exception(e)
```

### 示例 2: 使用 Site 导航方法

```python
# 使用示例
from src.tools.sites.xiaohongshu import XiaohongshuSite


async def navigate_to_feed_detail(note_id: str):
    """导航到笔记详情页"""
    site = XiaohongshuSite()
    await site.navigate("feed", note_id)
```

---

## 十五、参考资源

- Neurone 工具基类: `src/tools/base.py`
- Go MCP Server 实现: `xiaohongshu-mcp/mcp_handlers.go`
- Chrome Extension 实现: `xiaohongshu-mcp-extension-latest/background.js`
- 现有小红书工具: `src/tools/xhs/`
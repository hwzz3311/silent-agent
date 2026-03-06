# 业务RPA工具开发完整指南

> 文档版本: 2.0
> 更新日期: 2026-03-05
> 适用项目: SilentAgent 浏览器自动化系统

---

## 目录

1. [项目架构概述](#一项目架构概述)
2. [工具开发完整流程](#二工具开发完整流程)
3. [必需和可选的类属性](#三必需和可选的类属性)
4. [ExecutionContext 执行上下文](#四executioncontext-执行上下文)
5. [浏览器客户端获取方式](#五浏览器客户端获取方式)
6. [关键的生命周期方法](#六关键的生命周期方法)
7. [参数和结果类型定义规范](#七参数和结果类型定义规范)
8. [选择器系统实现](#八选择器系统实现)
9. [统一的异常体系](#九统一的异常体系)
10. [常见开发模式与注意事项](#十常见开发模式与注意事项)
11. [工具注册方式](#十一工具注册方式)
12. [开发检查清单](#十二开发检查清单)

---

## 一、项目架构概述

### 1.1 核心文件位置

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| 工具基类 | `src/tools/base.py` | Tool 抽象基类、参数类型、执行上下文 |
| 业务工具基类 | `src/tools/business/base.py` | BusinessTool 业务工具基类 |
| 站点适配器基类 | `src/tools/business/site_base.py` | Site 抽象基类 |
| 业务工具装饰器 | `src/tools/business/decorator.py` | @business_tool 装饰器 |
| 工具注册表 | `src/tools/business/registry.py` | BusinessToolRegistry 注册表 |
| 选择器系统 | `src/tools/sites/selectors/common.py` | 通用选择器定义 |
| 业务错误 | `src/tools/business/errors.py` | 业务错误定义 |
| 核心类型 | `src/core/result.py` | Result、Error、ResultMeta |
| 核心异常 | `src/core/exception.py` | 统一异常体系 |

### 1.2 工具层次结构

```
API 层 (FastAPI)
    ↓
工具层 (BusinessTool)
    ↓
站点适配器层 (Site)
    ↓
浏览器工具层 (chrome_navigate/click/fill/...)
```

### 1.3 支持的站点

| 站点 | 工具数量 | 目录 |
|------|----------|------|
| 小红书 | 16 | `src/tools/sites/xiaohongshu/tools/` |
| 闲鱼 | 2 | `src/tools/sites/xianyu/tools/` |

---

## 二、工具开发完整流程

### 2.1 步骤总览

```
定义参数类 → 定义结果类 → 创建工具类 → 实现核心逻辑 → 装饰器自动注册
```

### 2.2 步骤1: 定义参数类

**文件位置**: `src/tools/sites/[站点]/tools/[模块]/params.py`

```python
from src.tools.base import ToolParameters
from pydantic import Field
from typing import Optional, List

class XHSPublishContentParams(ToolParameters):
    """小红书发布图文内容工具参数

    参数说明：
    - tab_id: 标签页 ID，默认使用当前活动标签页
    - title: 笔记标题，1-100 字符
    - content: 正文内容，1-2000 字符
    - images: 图片路径列表（可选）
    - topic_tag: 话题标签列表（可选）
    - at_user: @用户列表（可选）
    """
    # 可选：标签页 ID
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID默认使用当前活动标签页"
    )

    # 必填：标题
    title: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="笔记标题"
    )

    # 必填：正文
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="正文内容"
    )

    # 可选：图片列表
    images: Optional[List[str]] = Field(
        default=None,
        description="图片路径列表，base64 或文件路径"
    )

    # 可选：话题标签
    topic_tag: Optional[List[str]] = Field(
        default=None,
        description="话题标签列表"
    )

    # 可选：@用户
    at_users: Optional[List[str]] = Field(
        default=None,
        description="@用户列表"
    )

    # 可选：位置信息
    location: Optional[str] = Field(
        default=None,
        description="位置信息"
    )
```

**关键特性**：
- 必须继承 `ToolParameters` 基类
- 使用 Pydantic `Field` 定义字段
- `...` 表示必填字段，`default` 表示可选字段
- 支持验证：min_length、max_length、ge、le、pattern 等

### 2.3 步骤2: 定义结果类

**文件位置**: `src/tools/sites/[站点]/tools/[模块]/result.py`

```python
from pydantic import BaseModel
from typing import Optional

class XHSPublishContentResult(BaseModel):
    """发布图文内容结果

    返回字段：
    - success: 是否成功
    - note_id: 笔记 ID（成功时返回）
    - url: 笔记链接（成功时返回）
    - message: 结果描述信息
    """
    success: bool = False
    note_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return self.model_dump() if hasattr(self, 'model_dump') else self.dict()
```

### 2.4 步骤3: 创建业务工具类

**文件位置**: `src/tools/sites/[站点]/tools/[模块]/[tool_name].py`

```python
import logging
from typing import TYPE_CHECKING

from src.tools.base import ExecutionContext
from src.tools.business import business_tool
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite

if TYPE_CHECKING:
    from .params import XHSPublishContentParams
    from .result import XHSPublishContentResult

# 创建日志记录器
logger = logging.getLogger("xhs_publish_content")


@business_tool(
    name="xhs_publish_content",
    site_type=XiaohongshuSite,
    operation_category="publish",
    required_login=True
)
class PublishContentTool(BusinessTool["XHSPublishContentParams"]):
    """发布小红书图文笔记工具

    功能说明：
    - 发布图文笔记到小红书平台
    - 支持添加标题、正文、图片、话题标签
    - 自动处理登录状态检查

    使用示例：
        tool = PublishContentTool()
        result = await tool.execute(
            params=XHSPublishContentParams(
                title="测试标题",
                content="测试内容",
                images=[]
            ),
            context=context
        )
    """

    name = "xhs_publish_content"
    description = "发布小红书图文笔记，支持添加标题、正文、图片、话题标签"
    version = "1.0.0"
    operation_category = "publish"
    required_login = True

    # Tab 管理属性
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/"

    @log_operation("xhs_publish_content")
    async def _execute_core(
        self,
        params: "XHSPublishContentParams",
        context: ExecutionContext,
    ) -> "XHSPublishContentResult":
        """核心执行逻辑

        参数:
            params: 工具参数
            context: 执行上下文

        返回:
            XHSPublishContentResult: 发布结果
        """
        # 1. 获取浏览器客户端（依赖注入）
        client = context.client
        if not client:
            return XHSPublishContentResult(
                success=False,
                message="无法获取浏览器客户端，请确保通过 API 调用"
            )

        # 2. 获取网站适配器
        site = self.get_site(context)

        # 3. 执行发布流程
        try:
            # 3.1 导航到发布页面
            await client.execute_tool("chrome_navigate", {
                "url": "https://www.xiaohongshu.com/publish/publish",
                "tabId": params.tab_id or context.tab_id
            })

            # 3.2 填写标题
            title_selector = site.selectors.publish_title_input
            await client.execute_tool("chrome_fill", {
                "selector": title_selector,
                "value": params.title,
                "tabId": params.tab_id or context.tab_id
            })

            # 3.3 填写正文
            content_selector = site.selectors.publish_content_input
            await client.execute_tool("chrome_fill", {
                "selector": content_selector,
                "value": params.content,
                "tabId": params.tab_id or context.tab_id
            })

            # 3.4 上传图片（如有）
            if params.images:
                for img_path in params.images:
                    # 上传图片逻辑
                    pass

            # 3.5 点击发布按钮
            publish_selector = site.selectors.publish_button
            await client.execute_tool("chrome_click", {
                "selector": publish_selector,
                "tabId": params.tab_id or context.tab_id
            })

            # 3.6 等待发布完成并获取结果
            note_id = await self._extract_note_id(client, params.tab_id or context.tab_id, site)

            return XHSPublishContentResult(
                success=True,
                note_id=note_id,
                url=f"https://www.xiaohongshu.com/discovery/{note_id}",
                message="发布成功"
            )

        except Exception as e:
            logger.exception(f"发布失败: {str(e)}")
            return XHSPublishContentResult(
                success=False,
                message=f"发布失败: {str(e)}"
            )

    async def _extract_note_id(self, client, tab_id, site):
        """提取发布的笔记 ID"""
        # 实现提取逻辑
        return "123456"


# ========== 便捷函数（可选） ==========

async def publish_content(
    title: str,
    content: str,
    images: list = None,
    topic_tag: list = None,
    tab_id: int = None,
    context: ExecutionContext = None
) -> "XHSPublishContentResult":
    """便捷的发布函数

    参数:
        title: 笔记标题
        content: 正文内容
        images: 图片列表
        topic_tag: 话题标签
        tab_id: 标签页 ID
        context: 执行上下文

    返回:
        XHSPublishContentResult: 发布结果
    """
    tool = PublishContentTool()
    params = XHSPublishContentParams(
        title=title,
        content=content,
        images=images,
        topic_tag=topic_tag,
        tab_id=tab_id
    )

    # 使用带重试的执行
    ctx = context or ExecutionContext()
    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSPublishContentResult(
            success=False,
            message=f"发布失败: {result.error}"
        )


__all__ = [
    "PublishContentTool",
    "publish_content",
    "XHSPublishContentParams",
    "XHSPublishContentResult",
]
```

---

## 三、必需和可选的类属性

### 3.1 必需类属性（通过 @business_tool 装饰器设置）

| 属性 | 类型 | 说明 | 方式 |
|------|------|------|------|
| `name` | str | 工具唯一名称 | 装饰器参数或自动生成 |
| `site_type` | Type[Site] | 对应的网站适配器类型 | 装饰器参数（必需） |

### 3.2 可选类属性（可覆盖）

| 属性 | 默认值 | 说明 |
|------|--------|------|
| `description` | `"业务操作工具"` | 工具描述说明 |
| `version` | `"1.0.0"` | 工具版本号 |
| `operation_category` | `"general"` | 操作分类：login/publish/browse/interact/general |
| `required_login` | `True` | 是否需要登录才能执行 |
| `target_site_domain` | `None` | 目标网站域名（用于 Tab 管理） |
| `default_navigate_url` | `None` | 默认导航 URL（用于 Tab 管理） |

### 3.3 Tab 管理相关属性

启用自动标签页管理需要设置：

```python
@business_tool(name="my_tool", site_type=MySite)
class MyTool(BusinessTool):
    # 启用自动 Tab 管理
    target_site_domain = "xiaohongshu.com"  # 网站域名
    default_navigate_url = "https://www.xiaohongshu.com/"  # 默认 URL
```

---

## 四、ExecutionContext 执行上下文

### 4.1 完整属性定义

```python
@dataclass
class ExecutionContext:
    """执行上下文 - 跨工具共享的运行时状态"""

    # 标签页相关
    tab_id: Optional[int] = None  # 当前标签页 ID

    # 执行环境
    world: str = "MAIN"  # 执行世界：MAIN/ISOLATED

    # 变量作用域
    variables: Dict[str, Any] = field(default_factory=dict)

    # 超时配置
    timeout: int = 30000  # 超时毫秒（默认 30 秒）
    retry_count: int = 1  # 当前重试次数
    retry_delay: int = 1000  # 重试间隔毫秒

    # 浏览器客户端（依赖注入）
    client: Any = None  # BrowserPort 接口实现

    # 认证信息
    secret_key: Optional[str] = None  # 插件密钥，用于多插件路由

    # 浏览器配置
    browser_mode: str = "extension"  # 浏览器客户端模式：extension/puppeteer/hybrid
```

### 4.2 依赖注入获取客户端

```python
async def _execute_core(self, params, context, site):
    # 方式1: 优先使用 context.client（推荐）
    client = context.client
    if not client:
        # 降级处理：创建默认客户端
        from src.adapters.relay import SilentAgentClient
        client = SilentAgentClient()
        await client.connect()

    # 使用客户端执行操作
    result = await client.execute_tool("chrome_navigate", {...})

    # 或使用端口抽象（推荐用于 API 层）
    from src.ports.browser_port_adapter import BrowserPortAdapter
    port = BrowserPortAdapter(client)
    await port.navigate(url="...")
```

---

## 五、浏览器客户端获取方式

### 5.1 核心方式：依赖注入

```python
async def _execute_core(self, params, context):
    # 通过 context.client 获取（推荐）
    client = context.client
    if not client:
        return MyToolResult(success=False, message="无法获取浏览器客户端")

    # 使用 client 执行浏览器操作
    result = await client.execute_tool("chrome_navigate", {
        "url": "https://example.com",
        "tabId": params.tab_id or context.tab_id
    })
```

### 5.2 Tab ID 获取

Tab ID 可以通过以下方式获取：

1. **参数传入**: `params.tab_id`（最高优先级）
2. **上下文获取**: `context.tab_id`
3. **手动创建**: 调用浏览器工具创建新标签页

```python
# 获取 tab_id
tab_id = params.tab_id or context.tab_id

# 如果没有 tab_id，需要先创建
if not tab_id:
    nav_result = await client.execute_tool("chrome_navigate", {
        "url": "https://www.xiaohongshu.com/",
        "newTab": True  # 创建新标签页
    })
    tab_id = nav_result.get("tabId")
```

---

## 六、关键的生命周期方法

### 6.1 执行流程图

```
execute() [入口]
    ↓
execute_with_retry() [带重试]
    ↓
execute_with_validation() [带验证]
        ├── validate_param()       # 参数验证
        ├── _pre_execute()          # 前置检查（登录状态等）
        ├── get_site()             # 获取网站适配器（单例）
        ├── _execute_core()        # 核心业务逻辑（子类必须实现）
        └── _post_execute()        # 后置处理
```

### 6.2 方法说明

| 方法 | 必须覆盖 | 默认行为 | 说明 |
|------|---------|---------|------|
| `_execute_core` | **是** | 抛出 NotImplementedError | 核心业务逻辑，子类必须实现 |
| `_pre_execute` | 否 | 检查登录 | 前置检查，可覆盖自定义逻辑 |
| `_post_execute` | 否 | 直接返回 | 后置处理，默认透传结果 |
| `validate_param` | 否 | Pydantic 验证 | 自定义参数验证逻辑 |
| `get_site` | 否 | 单例返回 | 获取网站适配器实例 |

### 6.3 _pre_execute 默认实现

```python
async def _pre_execute(
    self,
    params: ParamsT,
    context: ExecutionContext
) -> Result[bool]:
    """前置检查 - 默认检查登录状态"""
    # 如果不需要登录，跳过检查
    if not self.required_login:
        return Result.ok(data=True)

    # 获取网站适配器
    site = self.get_site(context)

    # 检查登录状态
    login_result = await site.check_login_status(context, silent=True)

    if login_result.success and login_result.data.get("is_logged_in"):
        return Result.ok(data=True)
    else:
        # 返回登录需要错误
        return Result.fail(
            error=Error(
                code=BusinessErrorCode.LOGIN_REQUIRED.value,
                message=f"需要登录后才能执行操作 {self.name}",
                recoverable=True,
                details={
                    "site_name": site.site_name,
                    "operation": self.name,
                    "suggestion": "请先调用登录工具或等待用户登录"
                }
            ),
            meta=ResultMeta(tool_name=self.name, duration_ms=0)
        )
```

---

## 七、参数和结果类型定义规范

### 7.1 参数类规范

```python
class MyToolParams(ToolParameters):
    """工具参数说明"""

    # 必填字段（使用 ... 表示）
    required_field: str = Field(
        ...,
        description="字段描述"
    )

    # 可选字段
    optional_field: Optional[str] = Field(
        default=None,
        description="字段描述"
    )

    # 带验证的字段
    validated_field: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z]+$"
    )

    # 数值字段
    count: int = Field(
        default=10,
        ge=1,
        le=100,
        description="数量限制 1-100"
    )

    # 列表字段
    items: Optional[List[str]] = Field(
        default_factory=list,
        description="列表字段"
    )

    # 枚举字段
    type: str = Field(
        default="default",
        description="类型：default/fast/custom"
    )
```

### 7.2 常用 Field 参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `default` | 默认值 | `default=None` |
| `default_factory` | 默认工厂 | `default_factory=list` |
| `description` | 字段描述 | `description="用户ID"` |
| `min_length` | 最小长度 | `min_length=1` |
| `max_length` | 最大长度 | `max_length=100` |
| `ge` | 最小值（数字） | `ge=1` |
| `le` | 最大值（数字） | `le=100` |
| `pattern` | 正则验证 | `pattern=r"^\d+$"` |

### 7.3 结果类规范

```python
class MyToolResult(BaseModel):
    """结果说明

    返回字段：
    - success: 是否成功
    - message: 结果描述
    - data: 业务数据（可选）
    """
    # 必须字段
    success: bool = False

    # 状态描述
    message: str = ""

    # 业务数据（根据工具不同而变化）
    note_id: Optional[str] = None
    url: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return self.model_dump() if hasattr(self, 'model_dump') else self.dict()
```

---

## 八、选择器系统实现

### 8.1 选择器层级结构

```
SiteSelectorSet (基类 - src/tools/business/site_base.py)
├── login_button: str
├── logout_button: str
├── user_avatar: str
├── modal_overlay: str
├── confirm_button: str
├── cancel_button: str
├── cookie_accept_button: str
└── ...更多通用选择器

    ↓ 继承
CommonFeedSelector (通用信息流)
├── feed_container: str
├── feed_card: str
├── feed_title: str
├── feed_author: str
├── feed_content: str
├── feed_likes: str
├── feed_comments: str
└── feed_collects: str

    ↓ 继承
XHSSelectors (小红书特定)
├── 继承所有父类选择器
├── 添加 xiaohongshu.com 特定的 CSS 选择器
├── publish_title_input: str
├── publish_content_input: str
├── publish_button: str
├── like_button: str
└── ...小红书特定
```

### 8.2 选择器获取方式

```python
# 方式1: 通过 site 实例直接访问
selector = site.selectors.feed_card

# 方式2: 通过 get_selector 方法
selector = site.get_selector("feed_card")

# 方式3: 使用 fallback（主选择器失败时使用备用）
selector = site.selectors.get_with_fallback(
    primary="feed_card",
    fallback_key="feed_card_alternatives"
)

# 方式4: 多选择器列表（按顺序尝试）
selectors = site.selectors.get_list("feed_card", "feed_item", "note-item")
```

---

## 九、统一的异常体系

### 9.1 业务错误码 (BusinessErrorCode)

```python
from enum import Enum

class BusinessErrorCode(str, Enum):
    """业务错误码枚举"""

    # 通用
    UNKNOWN = "UNKNOWN"

    # 登录相关 (1xxx)
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGIN_EXPIRED = "LOGIN_EXPIRED"
    LOGIN_INVALID = "LOGIN_INVALID"

    # 页面相关 (2xxx)
    PAGE_NOT_FOUND = "PAGE_NOT_FOUND"
    PAGE_LOAD_FAILED = "PAGE_LOAD_FAILED"
    PAGE_STRUCTURE_CHANGED = "PAGE_STRUCTURE_CHANGED"

    # 元素相关 (3xxx)
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_NOT_VISIBLE = "ELEMENT_NOT_VISIBLE"
    ELEMENT_NOT_INTERACTABLE = "ELEMENT_NOT_INTERACTABLE"
    ELEMENT_STALE = "ELEMENT_STALE"

    # 超时相关 (4xxx)
    TIMEOUT = "TIMEOUT"
    TIMEOUT_WAITING = "TIMEOUT_WAITING"
    TIMEOUT_DOWNLOAD = "TIMEOUT_DOWNLOAD"
    TIMEOUT_UPLOAD = "TIMEOUT_UPLOAD"

    # 数据提取相关 (5xxx)
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EXTRACTION_INVALID_FORMAT = "EXTRACTION_INVALID_FORMAT"

    # 验证相关 (6xxx)
    VALIDATION_FAILED = "VALIDATION_FAILED"
    VALIDATION_MISSING_FIELD = "VALIDATION_MISSING_FIELD"
    VALIDATION_INVALID_VALUE = "VALIDATION_INVALID_VALUE"

    # 网站相关 (7xxx)
    SITE_NOT_SUPPORTED = "SITE_NOT_SUPPORTED"
    SITE_STRUCTURE_CHANGED = "SITE_STRUCTURE_CHANGED"
    SITE_RESPONSE_ERROR = "SITE_RESPONSE_ERROR"

    # 频率限制 (8xxx)
    RATE_LIMITED = "RATE_LIMITED"
    RATE_LIMITED_API = "RATE_LIMITED_API"

    # 内部错误 (9xxx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INTERNAL_ASSERTION = "INTERNAL_ASSERTION"
```

### 9.2 业务异常类 (BusinessException)

```python
from src.tools.business.errors import BusinessException, BusinessErrorCode

# 方式1: 使用工厂方法
raise BusinessException.login_required("xiaohongshu")

raise BusinessException.element_not_found(
    selector=".like-button",
    operation="xhs_like_feed",
    suggestion="请检查页面结构是否变化"
)

# 方式2: 直接构造
raise BusinessException(
    code=BusinessErrorCode.ELEMENT_NOT_FOUND,
    message="找不到点赞按钮元素",
    details={
        "selector": ".like-button",
        "operation": "xhs_like_feed"
    },
    recoverable=True
)
```

---

## 十、常见开发模式与注意事项

### 10.1 模式1: 依赖注入获取客户端

```python
async def _execute_core(self, params, context, site):
    # 优先使用注入的客户端（推荐）
    client = context.client
    if not client:
        return MyResult(success=False, message="无浏览器客户端")

    # 执行浏览器操作
    result = await client.execute_tool("chrome_navigate", {
        "url": "https://example.com",
        "tabId": params.tab_id or context.tab_id
    })
```

### 10.2 模式2: 组合使用浏览器工具

```python
from src.tools.browser.fill import FillTool
from src.tools.browser.click import ClickTool
from src.tools.browser.wait import WaitTool

async def _execute_core(self, params, context, site):
    client = context.client

    # 等待元素出现
    wait_tool = WaitTool()
    await wait_tool.execute(
        params=wait_tool._get_params_type()(
            selector=".input-field",
            timeout=5000
        ),
        context=context
    )

    # 填写输入框
    fill_tool = FillTool()
    await fill_tool.execute(
        params=fill_tool._get_params_type()(
            selector=".input-field",
            value=params.value
        ),
        context=context
    )

    # 点击按钮
    click_tool = ClickTool()
    await click_tool.execute(
        params=click_tool._get_params_type()(
            selector=".submit-btn"
        ),
        context=context
    )
```

### 10.3 模式3: 返回结果对象

```python
async def _execute_core(self, params, context, site):
    # 成功结果
    return MyToolResult(
        success=True,
        note_id="123456",
        url="https://...",
        message="操作成功"
    )

    # 失败结果
    return MyToolResult(
        success=False,
        message="操作失败: 具体原因"
    )
```

### 10.4 模式4: 使用 Result 包装

```python
from src.core.result import Result, Error

async def _execute_core(self, params, context, site):
    # 返回 Result 包装的结果
    return Result.ok(
        data=MyToolResult(success=True, ...),
        meta=ResultMeta(
            tool_name=self.name,
            duration_ms=1500
        )
    )

    # 失败时
    return Result.fail(
        error=Error(
            code=BusinessErrorCode.OPERATION_FAILED,
            message="操作失败"
        )
    )
```

### 10.5 模式5: 日志记录

```python
from src.tools.business.logging import log_operation
import logging

logger = logging.getLogger(__name__)

class MyTool(BusinessTool):
    @log_operation("my_tool")  # 自动记录操作日志
    async def _execute_core(self, params, context, site):
        logger.info(f"开始执行工具: {self.name}")
        logger.debug(f"参数: {params}")

        try:
            # 业务逻辑
            result = ...

            logger.info(f"执行成功: {result}")
            return result

        except Exception as e:
            logger.error(f"执行失败: {e}")
            raise
```

### 10.6 注意事项清单

| # | 注意事项 | 说明 |
|---|---------|------|
| 1 | **优先使用 context.client** | 依赖注入式获取客户端，不使用旧的全局客户端 |
| 2 | **Tab 管理** | 使用 `params.tab_id or context.tab_id` 获取 Tab ID |
| 3 | **参数验证** | 使用 Pydantic Field 验证功能，避免业务代码中的手动验证 |
| 4 | **错误处理** | 使用 BusinessException 而非直接 raise Exception |
| 5 | **选择器降级** | 准备多个选择器，使用 `get_with_fallback` 处理网站结构变化 |
| 6 | **登录检查** | 设置 `required_login=True` 自动进行登录状态检查 |
| 7 | **返回值规范** | 返回 BaseModel 结果或 Result 包装的结果 |
| 8 | **tab_id 传递** | 所有浏览器操作都需要传递 tab_id 参数 |
| 9 | **异常恢复** | 设置 `recoverable=True` 允许重试恢复 |
| 10 | **超时处理** | 使用 context.timeout 控制操作超时 |

---

## 十一、工具注册方式

### 11.1 装饰器注册（推荐）

```python
from src.tools.business import business_tool
from src.tools.sites.xiaohongshu.adapters import XiaohongshuSite

@business_tool(
    name="xhs_check_login_status",
    site_type=XiaohongshuSite,
    operation_category="login",
    required_login=False
)
class CheckLoginStatusTool(BusinessTool):
    """检查小红书登录状态"""
    description = "检查小红书登录状态，返回用户名等信息"
    # ...
```

装饰器会自动：
- 设置 `name`、`operation_category`、`version`、`required_login` 属性
- 自动注册工具到 `BusinessToolRegistry`

### 11.2 手动注册

```python
from src.tools.business.registry import BusinessToolRegistry

# 注册工具类
BusinessToolRegistry.register_by_class(CheckLoginStatusTool)

# 或注册工具实例
BusinessToolRegistry.register(CheckLoginStatusTool())
```

### 11.3 模块级注册

```python
# src/tools/sites/xiaohongshu/tools/browse/__init__.py

from .list_feeds import ListFeedsTool
from .search_feeds import SearchFeedsTool
from .get_feed_detail import GetFeedDetailTool
from .user_profile import UserProfileTool

# 导入工具模块即可自动注册（装饰器自动完成）
__all__ = [
    "ListFeedsTool",
    "SearchFeedsTool",
    "GetFeedDetailTool",
    "UserProfileTool",
]
```

---

## 十二、开发检查清单

### 12.1 代码检查清单

在提交代码前，确认以下项目：

- [ ] 工具类继承 `BusinessTool[ParamT]`
- [ ] 使用 `@business_tool` 装饰器设置 `name` 和 `site_type`
- [ ] 设置 `operation_category` 操作分类
- [ ] 设置 `required_login` 是否需要登录
- [ ] 需要 Tab 管理时设置 `target_site_domain` 和 `default_navigate_url`
- [ ] 参数类继承 `ToolParameters`
- [ ] 结果类继承 `BaseModel`
- [ ] 使用 `context.client` 获取浏览器客户端
- [ ] 通过 `params.tab_id or context.tab_id` 获取 Tab ID
- [ ] 所有浏览器操作传递 `tabId` 参数
- [ ] 正确处理异常并返回结果

### 12.2 测试验证清单

- [ ] 执行 `pytest tests_api.py` 通过
- [ ] 执行 `pytest tests_xiaohongshu.py` 通过
- [ ] 特定工具测试 `pytest tests_xiaohongshu.py::test_xxx` 通过
- [ ] 多浏览器隔离测试通过
- [ ] 选择器降级逻辑测试通过

### 12.3 文档更新清单

- [ ] 更新 README.md 工具列表
- [ ] 更新 CLAUDE.md 如有架构变更
- [ ] 更新选择器定义（如有变化）
- [ ] 添加工具使用示例

---

## 附录A: 完整示例参考

以下文件提供了完整的工具实现参考：

| 文件 | 说明 |
|------|------|
| `src/tools/sites/xiaohongshu/tools/login/check_login_status.py` | 登录检查完整示例 |
| `src/tools/sites/xiaohongshu/tools/login/get_login_qrcode.py` | 登录二维码示例 |
| `src/tools/sites/xiaohongshu/tools/interact/like_feed.py` | 互动工具示例 |
| `src/tools/sites/xiaohongshu/tools/browse/list_feeds.py` | 浏览工具示例 |
| `src/tools/sites/xianyu/tools/publish/publish_item.py` | 闲鱼工具示例 |

---

## 附录B: 浏览器工具列表

| 工具名 | 功能 | 用途 |
|--------|------|------|
| `chrome_navigate` | 导航到 URL | 页面跳转 |
| `chrome_click` | 点击元素 | 按钮点击、链接跳转 |
| `chrome_fill` | 填写表单 | 输入文本 |
| `chrome_extract` | 提取数据 | 获取页面数据 |
| `chrome_screenshot` | 页面截图 | 截图保存 |
| `chrome_scroll` | 滚动页面 | 滚动操作 |
| `chrome_inject` | 注入脚本 | 执行自定义 JS |
| `chrome_evaluate` | 执行 JS | JS 表达式计算 |
| `chrome_wait` | 等待元素 | 等待加载 |
| `chrome_keyboard` | 键盘输入 | 模拟按键 |
| `chrome_a11y_tree` | 无障碍树 | 辅助功能树 |
| `chrome_control` | 浏览器控制 | Cookie管理等 |
| `read_page_data` | 读取页面数据 | 执行 JS 获取数据 |

---

*文档结束*

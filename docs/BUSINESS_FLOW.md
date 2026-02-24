# RPA 业务流程框架设计文档

## 概述

本文档描述了 Neurone RPA Server 的多平台业务流程框架设计，以小红书（Xiaohongshu）为例，说明工具实现、适配器模式、执行流程等核心概念。

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        API 层                                    │
│              (src/api/routes/execute.py)                        │
│                    ↓                                            │
│              执行请求路由                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      客户端层                                    │
│                (src/client/client.py)                           │
│                    ↓                                            │
│              execute_tool()                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     工具层                                       │
│                (src/tools/base.py)                              │
│  Tool[TParams, TResult] → BusinessTool[SiteT, ParamsT]         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   网站适配器层                                   │
│            (src/tools/business/site_base.py)                    │
│  Site[T] → XiaohongshuSite                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     浏览器层                                     │
│             (src/tools/browser/*.py)                            │
│     navigate, click, fill, extract, screenshot 等               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心类型定义

### 2.1 Result 类型（统一返回结果）

```python
# src/core/result.py

@dataclass
class Result(Generic[T]):
    """统一返回结果类"""
    success: bool                    # 是否成功
    data: Optional[T] = None         # 成功时的数据
    error: Optional[Error] = None    # 失败时的错误信息
    meta: Optional[ResultMeta] = None # 执行元数据

@dataclass
class Error:
    """错误信息"""
    code: str                        # 错误码
    message: str                     # 错误消息
    details: Optional[dict] = None   # 详细错误信息
    recoverable: bool = False        # 是否可恢复

@dataclass
class ResultMeta:
    """执行元数据"""
    tool_name: str                   # 工具名称
    duration_ms: int                 # 执行时长（毫秒）
    timestamp: datetime = ...        # 时间戳
    attempt: int = 1                 # 重试次数
```

**使用示例**：

```python
# 成功返回
return Result.ok(
    data={"is_logged_in": True, "username": "test"},
    meta=ResultMeta(tool_name="xhs_check_login_status", duration_ms=100)
)

# 失败返回
return Result.fail(
    error=Error.unknown(
        message="登录状态检查失败",
        details={"reason": str(e)}
    )
)
```

### 2.2 工具参数类型

```python
# src/tools/base.py

class ToolParameters(BaseModel):
    """工具参数基类（Pydantic BaseModel）"""
    class Config:
        extra = "forbid"  # 禁止额外字段
```

**使用示例**：

```python
# src/tools/sites/xiaohongshu/tools/login/params.py

class XHSCheckLoginStatusParams(ToolParameters):
    """小红书登录检查工具参数"""
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )
```

### 2.3 工具结果类型

```python
# src/tools/sites/xiaohongshu/tools/login/result.py

class XHSCheckLoginStatusResult(BaseModel):
    """小红书登录检查工具结果"""
    success: bool
    is_logged_in: bool = False
    username: Optional[str] = None
    user_id: Optional[str] = None
    avatar: Optional[str] = None
    message: str = ""
```

---

## 3. 工具基类层次结构

### 3.1 基础工具类 Tool

```python
# src/tools/base.py

class Tool(ABC, Generic[TParams, TResult]):
    """
    工具抽象基类

    所有工具都必须继承此类并实现以下方法：
    - execute(): 执行工具逻辑
    """
    name: str = "tool"
    description: str = "A tool"
    version: str = "1.0.0"
    category: str = "general"

    async def execute(
        self,
        params: TParams,
        context: ExecutionContext
    ) -> Result[TResult]:
        """执行工具逻辑（抽象方法）"""
        ...
```

### 3.2 业务工具类 BusinessTool

```python
# src/tools/business/base.py

class BusinessTool(
    Tool[ParamsT, Any],
    ABC,
    Generic[SiteT, ParamsT]
):
    """
    业务级 RPA 工具的抽象基类

    泛型参数：
    - SiteT: 网站适配器类型 (如 XiaohongshuSite)
    - ParamsT: 工具参数类型 (如 XHSCheckLoginStatusParams)

    必填类属性：
    - name: 工具名称
    - description: 工具描述
    - site_type: 对应的网站适配器类型
    - required_login: 是否需要登录

    可选覆盖方法：
    - _pre_execute(): 前置检查
    - _execute_core(): 核心业务逻辑
    - _post_execute(): 后置处理
    """
```

---

## 4. 执行流程详解

### 4.1 完整执行流程图

```
execute()
    ↓
execute_with_retry()
    ↓
    ┌─────────────────────────────────────────┐
    │  for attempt in 1..retry_count:        │
    │    ↓                                   │
    │  execute_with_validation()             │
    │    ↓                                   │
    │    ┌─────────────────────────────────┐  │
    │    │ 1. validate_params()           │  │
    │    │    - 验证参数格式               │  │
    │    │    - 返回 ValidationResult     │  │
    │    └─────────────────────────────────┘  │
    │    ↓                                   │
    │    ┌─────────────────────────────────┐  │
    │    │ 2. _pre_execute()              │  │
    │    │    - 检查登录状态               │  │
    │    │    - 返回 Result               │  │
    │    └─────────────────────────────────┘  │
    │    ↓                                   │
    │    ┌─────────────────────────────────┐  │
    │    │ 3. get_site(context)           │  │
    │    │    - 获取网站适配器实例         │  │
    │    │    - 单例模式缓存               │  │
    │    └─────────────────────────────────┘  │
    │    ↓                                   │
    │    ┌─────────────────────────────────┐  │
    │    │ 4. _execute_core()             │  │
    │    │    - 执行具体业务逻辑           │  │
    │    │    - 返回 Result 或 BaseModel  │  │
    │    └─────────────────────────────────┘  │
    │    ↓                                   │
    │    ┌─────────────────────────────────┐  │
    │    │ 5. _post_execute()             │  │
    │    │    - 自动包装非 Result 类型     │  │
    │    │    - 返回标准化 Result         │  │
    │    └─────────────────────────────────┘  │
    │    ↓                                   │
    │    根据 success 决定是否继续重试        │
    └─────────────────────────────────────────┘
```

### 4.2 关键方法详解

#### execute_with_validation()

```python
# src/tools/business/base.py:106

async def execute_with_validation(
    self,
    params: ParamsT,
    context: 'ExecutionContext'
) -> Result[Any]:
    """
    带验证的执行流程

    1. 参数验证 (validate_params)
    2. 前置检查 (_pre_execute)
    3. 获取网站适配器 (get_site)
    4. 核心执行 (_execute_core)
    5. 后置处理 (_post_execute)
    """
```

#### validate_params()

```python
# src/tools/base.py:258

async def validate_params(self, params: TParams) -> ValidationResult:
    """
    验证参数格式

    使用 _get_params_type() 获取实际参数类型：
    1. 优先使用 __parameters_type__ 属性
    2. 从 __orig_bases__ 获取泛型类型参数
    3. 对于 BusinessTool[XiaohongshuSite, ParamsT]，取 args[1]
    """
```

#### _get_params_type() - 关键！

```python
# src/tools/base.py:228

def _get_params_type(self) -> type:
    """
    获取参数类型（解决泛型 TypeVar 问题）

    BusinessTool[XiaohongshuSite, XHSCheckLoginStatusParams]
    └── __orig_bases__ = (BusinessTool[XiaohongshuSite, XHSCheckLoginStatusParams],)
    └── args[0] = XiaohongshuSite (Site 类型)
    └── args[1] = XHSCheckLoginStatusParams (Params 类型) ← 这是要返回的

    Returns:
        实际的参数类型（不是 TypeVar）
    """
```

#### _pre_execute()

```python
# src/tools/business/base.py:220

async def _pre_execute(
    self,
    params: ParamsT,
    context: 'ExecutionContext'
) -> Result[bool]:
    """
    前置检查（子类可覆盖）

    默认实现检查登录状态：
    1. 如果 required_login=False，跳过检查
    2. 调用 site.check_login_status()
    3. 未登录返回 Result.fail(LOGIN_REQUIRED)
    """
```

#### _execute_core()

```python
# src/tools/business/base.py:271

async def _execute_core(
    self,
    params: ParamsT,
    context: 'ExecutionContext',
    site: SiteT
) -> Result[Any]:
    """
    核心执行逻辑（子类必须实现）

    职责：
    - 调用 site 的方法执行具体操作
    - 返回 Result 或 BaseModel
    - 注意：会被 _post_execute 自动包装
    """
```

#### _post_execute()

```python
# src/tools/business/base.py:292

async def _post_execute(
    self,
    result: Result,
    params: ParamsT,
    context: 'ExecutionContext'
) -> Result[Any]:
    """
    后置处理（子类可覆盖）

    默认实现自动包装非 Result 类型：
    - 如果 result 是 BaseModel (如 XHSCheckLoginStatusResult)
    - 自动包装为 Result.ok(data=result)
    """
```

---

## 5. 网站适配器模式

### 5.1 Site 抽象基类

```python
# src/tools/business/site_base.py

class Site(ABC):
    """
    网站适配器抽象基类

    定义网站通用的 RPA 操作接口：
    - navigate(): 导航到页面
    - check_login_status(): 检查登录状态
    - extract_data(): 提取数据
    - wait_for_element(): 等待元素

    泛型参数：
    - ConfigT: 网站配置类型
    - SelectorsT: 选择器集合类型
    """
    config: ConfigT
    selectors: SelectorsT

    @abstractmethod
    async def navigate(self, page: str, page_id: str = None) -> Result[bool]:
        ...
```

### 5.2 小红书适配器 XiaohongshuSite

```python
# src/tools/sites/xiaohongshu/adapters.py

class XiaohongshuSite(Site):
    """
    小红书网站适配器

    实现小红书特定的 RPA 操作：
    - navigate(): 导航到首页、登录页、搜索页等
    - check_login_status(): 检查小红书登录状态
    - get_login_qrcode(): 获取登录二维码
    - delete_cookies(): 删除 Cookie
    - search(): 搜索内容
    - publish_content(): 发布图文笔记
    - like_feed(): 点赞
    - 等等...
    """

    # 网站配置
    config: XHSSiteConfig = XHSSiteConfig()

    # 选择器集合
    selectors: XHSSelectors = XHSSelectors()
```

### 5.3 适配器方法返回 Result

```python
# src/tools/sites/xiaohongshu/adapters.py:248

async def check_login_status(
    self,
    context: 'ExecutionContext' = None
) -> Result[Dict[str, Any]]:
    """
    检查小红书登录状态

    Returns:
        Result[Dict[str, Any]]: {
            "is_logged_in": bool,
            "username": Optional[str],
            "user_id": Optional[str],
            "avatar": Optional[str]
        }
    """
```

---

## 6. 工具实现示例：检查登录状态

### 6.1 工具类定义

```python
# src/tools/sites/xiaohongshu/tools/login/check_login_status.py

class CheckLoginStatusTool(BusinessTool[XiaohongshuSite, XHSCheckLoginStatusParams]):
    """
    检查小红书登录状态工具

    Usage:
        tool = CheckLoginStatusTool()
        result = await tool.execute(
            params=XHSCheckLoginStatusParams(),
            context=context
        )
        if result.success:
            print(f"已登录: {result.data.is_logged_in}")
    """

    name = "xhs_check_login_status"
    description = "检查小红书登录状态，返回用户名等信息"
    version = "1.0.0"
    category = "xiaohongshu"
    operation_category = "login"
    site_type = XiaohongshuSite
    required_login = False  # 此工具用于检查登录，不需要已登录

    async def _execute_core(
        self,
        params: XHSCheckLoginStatusParams,
        context: ExecutionContext,
        site: Site
    ) -> XHSCheckLoginStatusResult:
        """核心执行逻辑"""

        # 1. 调用适配器方法
        login_result = await site.check_login_status(context)

        if not login_result.success:
            return XHSCheckLoginStatusResult(
                success=False,
                is_logged_in=False,
                message=f"检查登录状态失败: {login_result.error}"
            )

        # 2. 解析结果
        login_data = login_result.data or {}

        return XHSCheckLoginStatusResult(
            success=True,
            is_logged_in=login_data.get("is_logged_in", False),
            username=login_data.get("username"),
            user_id=login_data.get("user_id"),
            avatar=login_data.get("avatar"),
            message=self._get_status_message(login_data)
        )
```

### 6.2 参数定义

```python
# src/tools/sites/xiaohongshu/tools/login/params.py

from src.tools.base import ToolParameters
from pydantic import Field
from typing import Optional

class XHSCheckLoginStatusParams(ToolParameters):
    """小红书登录检查工具参数"""
    tab_id: Optional[int] = Field(
        default=None,
        description="标签页 ID，默认使用当前活动标签页"
    )
```

### 6.3 结果定义

```python
# src/tools/sites/xiaohongshu/tools/login/result.py

from pydantic import BaseModel
from typing import Optional

class XHSCheckLoginStatusResult(BaseModel):
    """小红书登录检查工具结果"""
    success: bool
    is_logged_in: bool = False
    username: Optional[str] = None
    user_id: Optional[str] = None
    avatar: Optional[str] = None
    message: str = ""
```

### 6.4 便捷函数

```python
# src/tools/sites/xiaohongshu/tools/login/check_login_status.py

async def check_login_status(
    tab_id: int = None,
    context: ExecutionContext = None
) -> XHSCheckLoginStatusResult:
    """便捷的登录检查函数"""
    tool = CheckLoginStatusTool()
    params = XHSCheckLoginStatusParams(tab_id=tab_id)
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XHSCheckLoginStatusResult(
            success=False,
            is_logged_in=False,
            message=f"检查失败: {result.error}"
        )
```

---

## 7. 工具分类结构

```
src/tools/sites/xiaohongshu/tools/
├── login/                      # 登录相关
│   ├── check_login_status.py   # 检查登录状态
│   ├── get_login_qrcode.py     # 获取登录二维码
│   ├── delete_cookies.py       # 删除 Cookie
│   ├── wait_login.py           # 等待登录完成
│   ├── params.py               # 参数定义
│   └── result.py               # 结果定义
│
├── browse/                     # 浏览相关
│   ├── list_feeds.py           # 获取笔记列表
│   ├── get_feed_detail.py      # 获取笔记详情
│   ├── search_feeds.py         # 搜索笔记
│   ├── user_profile.py         # 获取用户主页
│   ├── params.py
│   └── result.py
│
├── interact/                   # 互动相关
│   ├── like_feed.py            # 点赞
│   ├── favorite_feed.py        # 收藏
│   ├── post_comment.py         # 发表评论
│   ├── reply_comment.py        # 回复评论
│   ├── params.py
│   └── result.py
│
├── publish/                    # 发布相关
│   ├── publish_content.py      # 发布图文
│   ├── publish_video.py        # 发布视频
│   ├── schedule_publish.py     # 定时发布
│   ├── check_publish_status.py # 检查发布状态
│   ├── params.py
│   └── result.py
│
└── __init__.py                 # 导出所有工具
```

---

## 8. 常见问题与解决方案

### 8.1 TypeVar 问题

**问题**：`_get_params_type()` 返回 TypeVar 而不是实际类型

**原因**：`BusinessTool[XiaohongshuSite, XHSCheckLoginStatusParams]` 中的泛型参数在运行时被擦除

**解决方案**：使用 `__orig_bases__` 获取类型参数

```python
# src/tools/base.py:228

def _get_params_type(self) -> type:
    orig_bases = getattr(self.__class__, '__orig_bases__', None)
    if orig_bases:
        for base in orig_bases:
            if hasattr(base, '__args__'):
                args = base.__args__
                if args and len(args) >= 2:
                    # BusinessTool[XiaohongshuSite, XHSCheckLoginStatusParams]
                    # args[0] = Site, args[1] = Params ← 取这个
                    arg1 = args[1]
                    if arg1 is not TParams and isinstance(arg1, type):
                        return arg1
```

### 8.2 Result.fail() 参数错误

**问题**：`Result.fail(message="xxx")` 报错

**原因**：`Result.fail()` 只接受 `error: Error` 参数

**解决方案**：

```python
# 错误
return Result.fail(message="xxx", details={...})

# 正确
from src.core.result import Error, Result

return Result.fail(
    error=Error.unknown(
        message="xxx",
        details={...}
    )
)
```

### 8.3 _execute_core 返回非 Result 类型

**问题**：`_execute_core` 返回 `BaseModel`，但期望 `Result`

**解决方案**：`_post_execute` 自动包装

```python
# src/tools/business/base.py:292

async def _post_execute(self, result, params, context):
    from src.core.result import Result as CoreResult

    # 自动包装非 Result 类型
    if not isinstance(result, CoreResult):
        if hasattr(result, 'success'):
            return CoreResult.ok(
                data=result,
                meta=ResultMeta(tool_name=self.name, duration_ms=0)
            )
    return result
```

### 8.4 ResultMeta 缺少必需参数

**问题**：`ResultMeta.__init__() missing 'duration_ms'`

**原因**：`duration_ms` 是必需参数

**解决方案**：

```python
# 错误
ResultMeta(tool_name=self.name)

# 正确
ResultMeta(
    tool_name=self.name,
    duration_ms=0  # 必须提供
)
```

---

## 9. 添加新平台适配器的步骤

### 步骤 1：创建适配器文件

```
src/tools/sites/[platform]/
├── adapters.py           # 适配器主文件
├── selectors.py          # 选择器定义
└── __init__.py
```

### 步骤 2：定义配置和选择器

```python
# src/tools/sites/[platform]/adapters.py

class [Platform]SiteConfig(SiteConfig):
    site_name: str = "[platform]"
    base_url: str = "https://www.[platform].com"

class [Platform]Selectors(SiteSelectorSet):
    # 定义平台特定的 CSS 选择器
    feed_card: str = ".feed-card"
    # ...
```

### 步骤 3：实现适配器类

```python
class [Platform]Site(Site):
    config: [Platform]SiteConfig = [Platform]SiteConfig()
    selectors: [Platform]Selectors = [Platform]Selectors()

    async def navigate(self, page: str, page_id: str = None) -> Result[bool]:
        # 实现导航逻辑
        ...
```

### 步骤 4：创建工具目录结构

```
src/tools/sites/[platform]/tools/
├── login/
│   ├── check_login_status.py
│   ├── params.py
│   └── result.py
├── browse/
├── interact/
└── publish/
```

### 步骤 5：实现具体工具

参考小红书工具实现模式，使用 `BusinessTool[PlatformSite, ParamsType]`。

---

## 10. API 调用流程

### 10.1 API 请求格式

```json
POST /api/v1/execute
{
    "tool": "xhs_check_login_status",
    "params": {
        "tab_id": null
    },
    "timeout": 60000
}
```

### 10.2 API 响应格式

```json
{
    "success": true,
    "data": {
        "success": true,
        "is_logged_in": false,
        "username": null,
        "message": "未登录"
    },
    "error": null,
    "meta": {
        "tool": "xhs_check_login_status",
        "duration_ms": 1500
    }
}
```

---

## 11. 附录：核心文件清单

| 文件 | 职责 |
|------|------|
| `src/core/result.py` | 定义 Result、Error、ResultMeta |
| `src/tools/base.py` | Tool 基类、参数类型、执行上下文 |
| `src/tools/business/base.py` | BusinessTool 基类 |
| `src/tools/business/site_base.py` | Site 抽象基类 |
| `src/tools/business/errors.py` | 业务错误定义 |
| `src/tools/business/registry.py` | 工具注册表 |
| `src/tools/sites/xiaohongshu/adapters.py` | 小红书适配器 |
| `src/tools/sites/xiaohongshu/tools/login/*.py` | 登录工具 |
| `src/tools/sites/xiaohongshu/tools/browse/*.py` | 浏览工具 |
| `src/tools/sites/xiaohongshu/tools/interact/*.py` | 互动工具 |
| `src/tools/sites/xiaohongshu/tools/publish/*.py` | 发布工具 |
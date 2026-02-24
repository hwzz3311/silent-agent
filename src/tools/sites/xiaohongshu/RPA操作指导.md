# RPA 工具开发规范

本文档为 RPA 系统的通用开发指引，适用于所有平台（如小红书、抖音、微信等）的业务工具开发。

---

## 一、系统架构概览

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   测试客户端    │ ──► │   REST API     │ ──► │   NeuroneClient │
│ (tests_*.py)    │      │  (execute.py)  │      │  (client.py)    │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                    │
                              ┌───────────────────────┘
                              ▼
                    ┌───────────────────────┐
                    │  BUSINESS_TOOLS     │
                    │  (业务工具映射)    │
                    └───────────────────────┘
                              │
                              ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Site 适配器   │ ◄── │ 业务工具实现   │ ◄── │  WebSocket    │
│ (adapter.py)  │      │ (tools/xxx/)    │      │  Relay Server  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                    │
                                                    ▼
                                          ┌─────────────────────┐
                                          │  Chrome Extension │
                                          │  (浏览器操作)    │
                                          └─────────────────────┘
```

### 工具分类

| 类型 | 名称示例 | 执行位置 | 调用方式 |
|-----|---------|---------|---------|
| 业务工具 | `xhs_check_login_status` | Python 端 | 直接执行 |
| 浏览器工具 | `browser_click`, `chrome_navigate` | Chrome 扩展 | WebSocket 转发 |

---

## 二、工具执行流程

### 完整执行链

```
API 请求 → Client 分发 → BusinessTool 执行 → Site 适配器 → 浏览器操作
```

### 1. API 请求入口

```json
{
    "tool": "xhs_check_login_status",
    "params": {},
    "timeout": 60000
}
```

### 2. Client 工具分发 (src/client/client.py)

```python
async def execute_tool(self, name: str, params: Dict, timeout: float = None, context=None):
    # 1. 检查是否是业务工具
    if name in BUSINESS_TOOLS:
        # 创建 ExecutionContext 并注入 client
        if context is None:
            context = ExecutionContext()
        context.client = self  # 注入 client 供业务工具使用

        # 执行业务工具
        result = await self._execute_business_tool(name, params, context)
        return self._format_result(name, result)

    # 2. 浏览器工具通过 relay_server 发送到 extension
    ...
```

### 3. 业务工具执行流程

```
execute() → execute_with_retry() → execute_with_validation() → _execute_core()
```

- `execute_with_retry()`: 处理重试逻辑
- `execute_with_validation()`: 执行前置检查、获取 site、执行核心逻辑
- `_execute_core()`: 工具的具体实现

---

## 三、业务工具开发规范

### 1. 目录结构

```
src/tools/sites/{platform}/
├── adapters.py          # Site 适配器
├── tools/
│   ├── login/           # 登录相关工具
│   │   ├── check_login_status.py
│   │   ├── get_login_qrcode.py
│   │   ├── delete_cookies.py
│   │   ├── params.py
│   │   └── result.py
│   ├── browse/          # 浏览相关工具
│   └── interact/       # 互动相关工具
```

### 2. 工具类模板

```python
"""
{平台} {功能}工具

实现 {tool_name} 工具，{功能描述}。
"""

import logging
from typing import Any

from src.tools.base import ExecutionContext
from src.tools.business.base import BusinessTool
from src.tools.business.logging import log_operation
from src.tools.business.site_base import Site
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.{platform}.adapters import {Platform}Site
from .params import XxxParams
from .result import XxxResult

# 创建日志记录器
logger = logging.getLogger("{tool_name}")


class XxxTool(BusinessTool[{Platform}Site, XxxParams]):
    """
    {功能描述}

    Usage:
        tool = XxxTool()
        result = await tool.execute(
            params=XxxParams(),
            context=context
        )

        if result.success:
            print(result.data.xxx)
    """

    name = "{tool_name}"
    description = "{工具描述}"
    version = "1.0.0"
    category = "{platform}"
    operation_category = "{login|browse|interact|publish}"
    site_type = {Platform}Site
    required_login = False  # 根据实际情况设置

    @log_operation("{tool_name}")
    async def _execute_core(
        self,
        params: XxxParams,
        context: ExecutionContext,
        site: Site
    ) -> Any:
        """
        核心执行逻辑

        Args:
            params: 工具参数
            context: 执行上下文（包含 client）
            site: 网站适配器实例

        Returns:
            XxxResult: 执行结果
        """
        # TODO: 实现核心逻辑
        pass

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)


# 便捷函数
async def xxx_function(
    param1: str = None,
    context: ExecutionContext = None
) -> XxxResult:
    """便捷执行函数"""
    tool = XxxTool()
    params = XxxParams(param1=param1)
    ctx = context or ExecutionContext()

    result = await tool.execute_with_retry(params, ctx)

    if result.success:
        return result.data
    else:
        return XxxResult(success=False, message=f"执行失败: {result.error}")


__all__ = ["XxxTool", "xxx_function", "XxxParams", "XxxResult"]
```

### 3. 参数和结果定义

#### 参数模板 (params.py)

```python
class XxxParams(ToolParameters):
    """
    {工具}参数

    Attributes:
        tab_id: 标签页 ID
        xxx: 其他参数
    """
    tab_id: Optional[int] = Field(default=None, description="标签页 ID")
    xxx: str = Field(default="...", description="参数描述")
```

#### 结果模板 (result.py)

```python
class XxxResult(BaseModel):
    """{工具}结果"""
    success: bool
    data: Any = None
    message: str = ""

    def to_dict(self) -> dict:
        return {"success": self.success, "data": self.data, "message": self.message}
```

---

## 四、浏览器操作规范

### 1. tab_id 管理（重要）

**优先级**：参数 `params.tab_id` → `context.tab_id` → 获取活动标签页 → 创建新标签页

```python
# 从 context 获取 client
client = getattr(context, 'client', None)
if not client:
    return XxxResult(success=False, message="无法获取浏览器客户端")

# 优先级获取 tab_id
tab_id = params.tab_id
if not tab_id:
    tab_id = context.tab_id

if not tab_id:
    # 获取当前活动标签页
    tab_result = await client.execute_tool("browser_control", {
        "action": "get_active_tab"
    }, timeout=10000)
    if tab_result.get("success") and tab_result.get("data"):
        tab_id = tab_result.get("data", {}).get("tabId")

if not tab_id:
    # 创建新标签页
    nav_result = await client.execute_tool("chrome_navigate", {
        "url": "https://www.xxx.com/",
        "newTab": True
    }, timeout=15000)
    if nav_result.get("success") and nav_result.get("data"):
        tab_id = nav_result.get("data", {}).get("tabId")

if not tab_id:
    return XxxResult(success=False, message="无法获取或创建标签页")
```

### 2. DOM 元素检测（多选择器遍历）

**核心原则**：网站页面结构可能变化，使用多个选择器依次尝试。

```python
# 定义多个可能的选择器
selectors = [
    "#app > div:nth-child(1) > div > div.login-container",  # 精确选择器
    ".login-container",                                    # 备选选择器
    "[class*='login-popup']",                             # 模糊匹配
]

for selector in selectors:
    # 步骤1: 检查元素是否存在
    check_code = "document.querySelector('" + selector + "') !== null"
    result = await client.execute_tool("inject_script", {
        "code": check_code,
        "tabId": tab_id
    }, timeout=1500)

    if result.get("success") and result.get("data") is True:
        logger.info(f"检测到元素: {selector}")
        # 步骤2: 获取元素属性
        js_code = "document.querySelector('" + selector + "').src"
        src_result = await client.execute_tool("inject_script", {
            "code": js_code,
            "tabId": tab_id
        }, timeout=1500)
        break
```

### 3. 多数据源尝试

**核心原则**：页面数据可能存在于多个全局变量中，依次尝试。

```python
# 多种可能的数据源
sources = [
    "__INITIAL_STATE__.explore.feeds",
    "__INITIAL_STATE__.note.feeds",
    "__NUXT__.data.0.feeds",
    "window.__FEEDS__",
]

for source in sources:
    result = await client.execute_tool("read_page_data", {
        "path": source,
        "tabId": tab_id
    }, timeout=15000)

    if result.get("success") and result.get("data"):
        data = result.get("data")
        if isinstance(data, list) and len(data) > 0:
            feeds_data = data
            logger.info(f"从 {source} 获取到 {len(feeds_data)} 条数据")
            break
```

### 4. browser_control 参数格式（重要坑点）

**参数必须包装在 `params` 字典中**：

```python
# ✅ 正确
await client.execute_tool("browser_control", {
    "action": "delete_cookies",
    "params": {
        "delete_all": True,
        "cookie_names": ["session_id", "token"]
    }
})

# ❌ 错误（会报 Pydantic 验证错误）
await client.execute_tool("browser_control", {
    "action": "delete_cookies",
    "delete_all": True
})
```

### 5. 常用浏览器工具

| 工具名称 | 功能 | 常用参数 |
|---------|------|---------|
| `inject_script` | 执行 JavaScript | `code`, `tabId` |
| `read_page_data` | 读取页面数据 | `path`, `tabId` |
| `browser_click` | 点击元素 | `selector`, `tabId` |
| `chrome_navigate` | 导航到 URL | `url`, `newTab` |
| `browser_control` | 浏览器控制 | `action`, `params` |

---

## 五、错误处理规范

### 1. 错误消息输出

**注意**：Error 对象不能直接转为字符串输出，必须获取 message 属性。

```python
# ✅ 正确
error_msg = extract_result.error.message if extract_result.error else "未知错误"
return XxxResult(success=False, message=f"获取失败: {error_msg}")

# ❌ 错误（会输出对象地址）
return XxxResult(success=False, message=f"获取失败: {extract_result.error}")
```

### 2. 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|-----|-----|---------|
| `AttributeError: object has no attribute 'error_from_exception'` | Site 基类缺少方法 | 在 `site_base.py` 中添加该方法 |
| `'str' object has no attribute 'get'` | 返回结果格式不对 | 检查工具返回的数据结构，使用 `.get()` 前判断类型 |
| `Extra input are not permitted` | browser_control 参数格式错误 | 操作参数放入 `params` 字典 |
| 浏览器扩展未连接 | relay_server 未启动或扩展未连接 | 确保 relay_server 运行且 Chrome 扩展已安装 |

### 3. 日志规范

```python
import logging

logger = logging.getLogger("tool_name")

# 不同级别日志
logger.info("开始执行...")           # 关键步骤
logger.debug(f"参数: {params}")      # 调试信息
logger.warning("备选方案尝试中")   # 警告
logger.error("执行失败: {error}")  # 错误
logger.exception("异常详情")       # 带堆栈的错误
```

---

## 六、登录相关工具开发模式

### 检查登录状态

1. 获取/创建标签页
2. 检测 DOM 元素（头像、用户名等）
3. 尝试从全局变量获取用户信息
4. 检查登录标识字段（isLogin, uid, userId 等）

### 获取登录二维码

1. 导航到登录页面
2. 等待页面加载
3. 多选择器遍历检测二维码元素
4. 获取二维码图片 URL

### 删除 Cookie

1. 调用 browser_control 工具
2. 参数格式必须为 `{action: "delete_cookies", params: {...}}`
3. 返回删除结果

---

## 七、关键文件说明

| 文件 | 说明 |
|------|------|
| `client/client.py` | 客户端核心，执行工具分发 |
| `api/routes/execute.py` | API 路由处理 |
| `tools/base.py` | 基础类定义 (ExecutionContext, ToolParameters) |
| `tools/business/base.py` | BusinessTool 基类 |
| `tools/business/site_base.py` | Site 抽象基类 |
| `tools/business/errors.py` | 错误定义 (BusinessException, Error) |
| `tools/business/registry.py` | 工具注册表 |
| `core/result.py` | Result 统一返回类 |
| `relay_client.py` | WebSocket 客户端 |
| `relay_server.py` | WebSocket 中继服务器 |

---

## 八、开发检查清单

新建工具时，确保完成以下事项：

- [ ] 在 `tools/business/__init__.py` 或对应平台注册工具
- [ ] 定义 Params 类（继承 ToolParameters）
- [ ] 定义 Result 类（继承 BaseModel）
- [ ] 实现 BusinessTool 子类
- [ ] 实现 `_execute_core` 方法
- [ ] 添加日志记录器
- [ ] 实现 tab_id 管理逻辑
- [ ] 实现多选择器遍历检测
- [ ] 实现错误消息正确输出
- [ ] 添加便捷函数（可选）
- [ ] 测试工具执行流程
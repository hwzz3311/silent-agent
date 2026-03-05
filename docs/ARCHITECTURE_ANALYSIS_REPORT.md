# 架构分析报告：SilentAgent 浏览器自动化系统

> 生成日期：2026-03-05
> 更新时间：2026-03-06（已解决 10 个问题，待解决 2 个问题）

## 项目概述

这是一个 **Chrome 扩展 + Python 控制器** 的 RPA (机器人流程自动化) 系统，通过 `chrome.scripting` API + WebSocket 实现远程浏览器控制。

## 架构亮点 ✅

| 特性 | 评价 | 说明 |
|------|------|------|
| **端口抽象** | ⭐⭐⭐⭐⭐ | `BrowserPort` 抽象接口，支持多客户端切换 |
| **依赖注入** | ⭐⭐⭐⭐⭐ | `ExecutionContext.client` 解耦工具与客户端 |
| **统一异常** | ⭐⭐⭐⭐⭐ | `ToolException` + 11 个子类，标准化错误处理 |
| **多浏览器** | ⭐⭐⭐⭐ | `BrowserManager` 支持多实例 + `browser_id` 路由 |
| **工作流引擎** | ⭐⭐⭐⭐ | `FlowEngine` 支持步骤编排、条件分支、循环 |
| **录制回放** | ⭐⭐⭐⭐ | `RecordingPlayer` 支持选择器降级、回放控制 |

---

## ✅ 已解决的问题

### 问题 1：重复抽象（BrowserClient vs BrowserPort）

**状态：已解决**（提交 c452bab）

- 删除了 `src/browser/base.py`（BrowserClient 抽象基类）
- 删除了 `src/ports/browser_port_adapter.py`（适配器）
- 补充了 BrowserPort 接口方法（scroll, keyboard）
- 修改具体客户端直接继承 BrowserPort，返回 Result 类型

### 问题 7：BrowserConfig 和 BrowserSettings 职责重叠

**状态：已解决**（提交 e566401）

- `BrowserSettings` 添加 `from_env()` 方法
- 删除 `client_factory.py` 中的重复 `BrowserConfig` 类
- 改为导入 `config.py` 的 `BrowserSettings` 并保留别名兼容
- 代码净减少 27 行

### 问题 2：泛型使用过于复杂

**状态：已解决**（提交 7b6881c）

- 移除 `BusinessTool[ParamT, ResultT]` 双泛型，改用单泛型
- `@business_tool` 装饰器新增 `param_type` 参数传入参数类型
- `Tool` 类添加 `__class_getitem__` 支持旧式泛型语法兼容
- 迁移 16 个小红书工具、4 个闲鱼工具、12 个浏览器工具
- 统一工具类声明语法，简化继承关系

### 问题 5：全局状态管理

**状态：已解决**（提交 00252e4）

- 为 `config.py` 添加 `set_config()` / `reset_config()` 注入函数
- 为 `browser/manager.py` 添加 `set_manager()` / `reset_manager()` 注入函数
- 为 `tools/registry.py` 添加 `set_registry()` / `reset_registry()` 注入函数
- 为 `tools/domain/registry.py` 添加 `set_registry()` / `reset_registry()` 注入函数
- 为 `selector/*/manager.py` 添加 `set_selector_manager()` / `reset_selector_manager()` 注入函数
- 所有全局状态现在支持测试时注入 mock 对象

### 问题 8：HybridClient 职责不清晰

**状态：已解决**（提交 52004f8）

- 新增 `src/browser/router.py`：提取路由策略到独立模块
- 新增 `DefaultRoutingStrategy` 类定义操作分类：
  - `PUPPETEER_ONLY`: navigate, screenshot, get_a11y_tree, list_tabs, get_active_tab
  - `EXTENSION_PREFERRED`: click, fill, extract, scroll, keyboard, wait_for
  - `FLEXIBLE`: evaluate, inject
- `HybridClient` 使用路由策略简化 12 个方法
- 代码净减少约 150 行，职责更清晰

### 问题 9：BusinessToolExecutor 硬编码工具映射

**状态：已解决**（提交 875cd51）

- 移除 `src/tools/executor.py` 中的 `BUSINESS_TOOLS` 硬编码字典
- 改用 `BusinessToolRegistry` 作为单一真相来源
- 自动利用 `@business_tool` 装饰器的自动注册功能
- 代码净减少约 90 行

---

## 🔵 待解决的问题

### 问题 3：模块边界模糊

| 模块 | 问题 | 状态 |
|------|------|------|
| `client/` vs `browser/` | 职责重叠 | 🔵 待解决 |
| `tools/browser/` vs `tools/business/` | 基础工具和业务工具混在一起 | 🔵 待解决 |
| 选择器管理 | 两处重复定义 | ✅ 已解决 |

**重构方案**: 见 `docs/REFACTORING_MODULE_BOUNDARY.md`

### 问题 4：层级过深

API → ToolExecutor → BusinessTool → Site Adapter → BrowserPort → 客户端，调用链过长。

### 问题 5：全局状态管理 ✅ 已解决

**问题**：`config.py`、`browser/manager.py`、`tools/base.py` 都使用全局单例/类变量，测试困难。

**涉及位置**：
- `src/config.py`：全局 `_config` 变量
- `src/browser/manager.py`：类变量 `_instances`、`_default_instance_id`
- `src/tools/registry.py`：`default_registry` 单例
- `src/tools/domain/registry.py`：`BusinessToolRegistry` 单例模式
- `src/tools/selector/*/manager.py`：`GlobalSelectorManager` 单例模式

**解决方案**：添加依赖注入支持，为每个全局状态添加：

| 模块 | 注入函数 | 重置函数 |
|------|----------|----------|
| `config.py` | `set_config()` | `reset_config()` |
| `browser/manager.py` | `set_manager()` | `reset_manager()` |
| `tools/registry.py` | `set_registry()` | `reset_registry()` |
| `tools/domain/registry.py` | `set_registry()` | `reset_registry()` |
| `selector/*/manager.py` | `set_selector_manager()` | `reset_selector_manager()` |

**使用示例**：

```python
# 测试时注入 mock
from src.config import set_config, reset_config
from src.tools.domain.registry import set_registry, reset_registry

mock_config = AppConfig()
set_config(mock_config)
# ... 测试代码
reset_config()

# 测试 BrowserManager
from src.browser.manager import BrowserManager
BrowserManager.reset_manager()
```

---

## 🔵 新发现的问题

### 问题 10：Site 单例缓存可能导致状态问题 ✅ 已解决

**位置**: `src/tools/business/base.py:351-353`

```python
# 使用单例模式缓存站点实例
if not hasattr(self, '_site_instance') or self._site_instance is None:
    self._site_instance = self.site_type()
```

**解决**：移除单例缓存，`get_site()` 每次创建新实例，避免状态共享

### 问题 11：动态导入无缓存 ✅ 已解决

**位置**: `src/tools/executor.py:114-115`

```python
# 动态导入模块和函数
module = importlib.import_module(module_path)
func = getattr(module, func_name)
```

**解决**：问题9修复时已一起解决 - 移除硬编码映射后改用 `BusinessToolRegistry`，内部维护 `_name_to_class` 字典存储类引用。`create_instance()` 直接从内存获取类，无需每次动态导入模块。

### 问题 12：选择器获取逻辑错误 ✅ 已解决

**位置**: `src/tools/business/base.py:376-381`

```python
# 首先检查工具自己的选择器
if hasattr(self, 'selectors'):
    site = self.get_site()
    selector = getattr(site.selectors, key, None)
```

**解决**：修复了选择器获取逻辑，优先使用工具自己（`self.selectors`）的选择器，如果没有再从 site 适配器获取。

---

## 总结

| 维度 | 评分 | 说明 |
|------|------|------|
| 抽象必要性 | ⭐⭐⭐⭐ | 端口抽象统一 |
| 泛型复杂度 | ⭐⭐⭐⭐ | 通过装饰器传入类型，简化泛型 |
| 模块粒度 | ⭐⭐⭐ | 边界有重叠 |
| 依赖管理 | ⭐⭐⭐⭐ | 依赖注入做得不错 |
| 全局状态 | ⭐⭐ | 需要改进 |

**优先改进建议：**
1. 移除全局变量（改用依赖注入）
2. 合并选择器模块
3. 简化调用链层级

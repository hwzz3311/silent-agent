# BusinessTool 泛型重构任务计划

## 概述

本文档描述将 `BusinessTool` 从双泛型参数模式改为类属性模式的改造计划。

## 问题背景

### 当前问题

`BusinessTool` 基类定义需要两个类型参数：

```python
class BusinessTool(Tool[ParamsT, Any], ABC, Generic[SiteT, ParamsT]):
    #                    ↑一个        ↑两个（SiteT, ParamsT）必需
```

但很多工具只传了一个参数，导致 `TypeError`:

```python
class SearchItemTool(BusinessTool[XYSearchItemParams]):  # 错误！
class PublishItemTool(BusinessTool[XYPublishItemParams]):  # 错误！
```

### 涉及文件统计

| 分类 | 数量 |
|------|------|
| 问题工具（仅1个泛型） | 8个 |
| 正确工具（2个泛型） | 13个 |
| 待修改基类文件 | 1个 |

---

## 改动方案

### 方案 B：移除 SiteT 泛型，改用类属性

**核心思路**：移除 `Generic[SiteT, ParamsT]`，将 `site_type` 从泛型改为可选类属性。

---

## 任务清单

### 任务 1：修改 BusinessTool 基类

**文件**: `src/tools/business/base.py`

| 检查项 | 当前状态 | 修改目标 |
|--------|----------|----------|
| 类继承 | `Generic[SiteT, ParamsT]` | 移除 `Generic[SiteT, ParamsT]` |
| `site_type` 定义 | `site_type: Type[SiteT]` | `site_type: Optional[type] = None` |
| `get_site` 方法 | 使用 `self.site_type()` | 添加 `site_type is None` 的处理逻辑 |
| `_execute_core` 签名 | `site: SiteT` 参数 | 改为 `site: Optional[Any] = None` |
| `get_info` 方法 | 访问 `cls.site_type.__name__` | 添加 None 检查 |
| 类型导入 | `TypeVar, Type` | 清理不需要的导入 |

**修改后预期**：

```python
class BusinessTool(Tool[ParamsT, Any], ABC):  # 不再需要 Generic
    # ...
    site_type: Optional[type] = None  # 可选类属性

    def get_site(self, context=None) -> Optional[Site]:
        if self.site_type is None:
            return None  # 或者抛出明确异常
        # ... 原有逻辑
```

---

### 任务 2：修复问题工具（添加 site_type 类属性）

需要为以下 8 个工具添加 `site_type` 类属性：

#### 2.1 闲鱼工具（2个）

| 文件 | 工具类 | 需要添加的 site_type |
|------|--------|---------------------|
| `tools/sites/xianyu/tools/publish/publish_item.py` | `PublishItemTool` | `XianyuSite` |
| `tools/sites/xianyu/tools/search/search_item.py` | `SearchItemTool` | `XianyuSite` |

#### 2.2 小红书工具（6个）

| 文件 | 工具类 | 需要添加的 site_type |
|------|--------|---------------------|
| `tools/sites/xiaohongshu/tools/login/check_login_status.py` | `CheckLoginStatusTool` | `XiaohongshuSite` |
| `tools/sites/xiaohongshu/tools/login/delete_cookies.py` | `DeleteCookiesTool` | `XiaohongshuSite` |
| `tools/sites/xiaohongshu/tools/login/wait_login.py` | `WaitLoginTool` | `XiaohongshuSite` |
| `tools/sites/xiaohongshu/tools/browse/list_feeds.py` | `ListFeedsTool` | `XiaohongshuSite` |
| `tools/sites/xiaohongshu/tools/browse/search_feeds.py` | `SearchFeedsTool` | `XiaohongshuSite` |
| `tools/sites/xiaohongshu/tools/publish/check_publish_status.py` | `CheckPublishStatusTool` | `XiaohongshuSite` |

**修改方式**：在每个工具类中添加：

```python
class XxxTool(BusinessTool[XxxParams]):  # 保持现有泛型声明
    # ... 其他属性
    site_type = XianyuSite  # 添加这个类属性
```

---

### 任务 3：验证测试

**验证方式**：导入工具模块，检查是否还有 TypeError

```python
# 测试导入
from src.tools.sites.xianyu.tools.search import SearchItemTool
from src.tools.sites.xiaohongshu.tools.login import CheckLoginStatusTool

# 验证 site_type 属性存在
assert SearchItemTool.site_type is not None
assert CheckLoginStatusTool.site_type is not None
```

---

## 改动详细列表

### 文件修改清单

| 序号 | 文件路径 | 修改类型 | 修改内容 |
|------|----------|----------|----------|
| 1 | `src/tools/business/base.py` | 重构 | 移除 Generic[SiteT, ParamsT]，改用类属性 |
| 2 | `tools/sites/xianyu/tools/publish/publish_item.py` | 增强 | 添加 `site_type = XianyuSite` |
| 3 | `tools/sites/xianyu/tools/search/search_item.py` | 增强 | 添加 `site_type = XianyuSite` |
| 4 | `tools/sites/xiaohongshu/tools/login/check_login_status.py` | 增强 | 添加 `site_type = XiaohongshuSite` |
| 5 | `tools/sites/xiaohongshu/tools/login/delete_cookies.py` | 增强 | 添加 `site_type = XiaohongshuSite` |
| 6 | `tools/sites/xiaohongshu/tools/login/wait_login.py` | 增强 | 添加 `site_type = XiaohongshuSite` |
| 7 | `tools/sites/xiaohongshu/tools/browse/list_feeds.py` | 增强 | 添加 `site_type = XiaohongshuSite` |
| 8 | `tools/sites/xiaohongshu/tools/browse/search_feeds.py` | 增强 | 添加 `site_type = XiaohongshuSite` |
| 9 | `tools/sites/xiaohongshu/tools/publish/check_publish_status.py` | 增强 | 添加 `site_type = XiaohongshuSite` |

### 导入依赖说明

#### 闲鱼工具需要添加的导入

```python
# publish_item.py / search_item.py 顶部添加：
from src.tools.sites.xianyu import XianyuSite
```

#### 小红书工具需要添加的导入

```python
# check_login_status.py 等文件顶部添加：
from src.tools.sites.xiaohongshu import XiaohongshuSite
```

---

## 确认方案

执行前请确认：

- [x] 理解改动方案：移除泛型参数，改用类属性
- [x] 了解影响范围：9 个文件需要修改
- [x] 知道风险：修改基类可能影响所有工具
- [x] 准备好回滚方案：保留当前代码备份

---

## 执行顺序

1. **先修改基类** (`src/tools/business/base.py`)
2. **逐个修复工具**（按表格顺序）
3. **运行验证测试**（确认无 TypeError）
4. **运行功能测试**（确保工具仍能正常工作）

---

## 预计影响

| 方面 | 影响 |
|------|------|
| 兼容性 | 向后兼容，现有正确工具仍可用 |
| 性能 | 无影响 |
| 维护性 | 简化泛型复杂度，更易理解 |
| 类型检查 | 需要更新 mypy/pyright 配置 |

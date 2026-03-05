# 工具注册机制优化 - 装饰器自动注册

> 任务规划文档
> 生成日期: 2026-03-05

---

## 一、当前模式分析

### 1.1 现有注册流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     现有注册流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                         │
│  工具类定义 (xxx.py)                                      │
│  ├── name = "xxx"                                        │
│  ├── site_type = XxxSite                                │
│  ├── @classmethod                                       │
│  │   └── def register(cls):  ← 重复代码                 │
│  │       return BusinessToolRegistry.register_by_class(cls) │
│                                                         │
│  模块 __init__.py                                        │
│  ├── def register():                                    │
│  │   ├── BusinessToolRegistry.register_by_class(Tool1)│
│  │   ├── BusinessToolRegistry.register_by_class(Tool2)│
│  │   └── BusinessToolRegistry.register_by_class(Tool3)│  ← 手动维护
│                                                         │
│  顶层 __init__.py                                       │
│  ├── def register_xxx_tools():                         │
│  │   ├── login_register()                              │
│  │   ├── publish_register()                            │
│  │   ├── browse_register()                            │
│  │   └── interact_register()                          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 问题总结

| 问题 | 说明 | 影响 |
|------|------|------|
| **重复代码** | 每个工具类都有相同的 `register` 方法 | 18 个工具 = 18 份重复 |
| **手动维护** | 新增工具需要在 `__init__.py` 手动添加注册 | 易遗漏、繁琐 |
| **职责不清** | 注册逻辑分散在类方法和模块中 | 维护困难 |

### 1.3 现有资源

BusinessToolRegistry 已提供自动发现功能：
- `discover_from_module(module, prefix)` - 从模块自动发现
- `discover_from_package(package_name, prefix)` - 从包自动发现

但当前**未使用**，仍采用手动注册模式。

---

## 二、优化方案设计

### 2.1 目标模式

```
┌─────────────────────────────────────────────────────────────────┐
│                     目标注册流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                         │
│  工具类定义 (xxx.py)                                      │
│  @business_tool(name="xxx", site_type=XxxSite)         ← 装饰器      │
│  class XxxTool(BusinessTool[...]):                     │
│      name = "xxx"                                        │
│      description = "..."                                │
│      # 无需定义 register 方法                           │
│                                                         │
│  模块 __init__.py (简化版)                              │
│  def register():                                        │
│      return BusinessToolRegistry.discover_from_module(  ← 自动发现│
│          sys.modules[__name__], prefix="xxx_"          │
│      )                                                  │
│                                                         │
│  顶层 __init__.py (不变)                                │
│  ├── register_xxx_tools() → 调用各模块 register()    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 方案对比

| 维度 | 当前模式 | 目标模式 |
|------|----------|----------|
| 工具类代码 | 需要定义 register 方法 | 使用装饰器 |
| 模块注册 | 手动逐个调用 register_by_class | 自动发现 |
| 新增工具 | 2 处修改（类 + __init__） | 仅 1 处（装饰器参数） |
| 代码重复 | 18 处 | 0 处 |

---

## 三、任务清单

### 3.1 需要检查的文件

#### 阶段 1: 基础设施（1 个文件）

| # | 文件 | 任务 |
|---|------|------|
| 1 | `src/tools/business/__init__.py` | 确认装饰器导出（已有 discover_and_register） |

#### 阶段 2: 小红书工具（16 个文件）

| # | 文件 | 判断条件 |
|---|------|----------|
| 1 | `src/tools/sites/xiaohongshu/tools/login/check_login_status.py` | 有 register 方法? |
| 2 | `src/tools/sites/xiaohongshu/tools/login/get_login_qrcode.py` | 有 register 方法? |
| 3 | `src/tools/sites/xiaohongshu/tools/login/wait_login.py` | 有 register 方法? |
| 4 | `src/tools/sites/xiaohongshu/tools/login/delete_cookies.py` | 有 register 方法? |
| 5 | `src/tools/sites/xiaohongshu/tools/browse/list_feeds.py` | 有 register 方法? |
| 6 | `src/tools/sites/xiaohongshu/tools/browse/get_feed_detail.py` | 有 register 方法? |
| 7 | `src/tools/sites/xiaohongshu/tools/browse/search_feeds.py` | 有 register 方法? |
| 8 | `src/tools/sites/xiaohongshu/tools/browse/user_profile.py` | 有 register 方法? |
| 9 | `src/tools/sites/xiaohongshu/tools/interact/like_feed.py` | 有 register 方法? |
| 10 | `src/tools/sites/xiaohongshu/tools/interact/favorite_feed.py` | 有 register 方法? |
| 11 | `src/tools/sites/xiaohongshu/tools/interact/post_comment.py` | 有 register 方法? |
| 12 | `src/tools/sites/xiaohongshu/tools/interact/reply_comment.py` | 有 register 方法? |
| 13 | `src/tools/sites/xiaohongshu/tools/publish/publish_content.py` | 有 register 方法? |
| 14 | `src/tools/sites/xiaohongshu/tools/publish/publish_video.py` | 有 register 方法? |
| 15 | `src/tools/sites/xiaohongshu/tools/publish/schedule_publish.py` | 有 register 方法? |
| 16 | `src/tools/sites/xiaohongshu/tools/publish/check_publish_status.py` | 有 register 方法? |

#### 阶段 3: 闲鱼工具（2 个文件）

| # | 文件 | 判断条件 |
|---|------|----------|
| 1 | `src/tools/sites/xianyu/tools/login/get_cookies.py` | 有 register 方法? |
| 2 | `src/tools/sites/xianyu/tools/publish/publish_item.py` | 有 register 方法? |

#### 阶段 4: 模块注册文件（6 个文件）

| # | 文件 | 任务 |
|---|------|------|
| 1 | `src/tools/sites/xiaohongshu/tools/login/__init__.py` | 改为自动发现 |
| 2 | `src/tools/sites/xiaohongshu/tools/browse/__init__.py` | 改为自动发现 |
| 3 | `src/tools/sites/xiaohongshu/tools/interact/__init__.py` | 改为自动发现 |
| 4 | `src/tools/sites/xiaohongshu/tools/publish/__init__.py` | 改为自动发现 |
| 5 | `src/tools/sites/xianyu/tools/publish/__init__.py` | 改为自动发现 |
| 6 | `src/tools/sites/xianyu/tools/search/__init__.py` | 改为自动发现（若有） |

#### 阶段 5: 站点顶层文件（2 个文件）

| # | 文件 | 任务 |
|---|------|------|
| 1 | `src/tools/sites/xiaohongshu/__init__.py` | 确认 register_xhs_tools |
| 2 | `src/tools/sites/xianyu/__init__.py` | 确认工具注册方式 |

**总计**: 约 27 个文件需要检查/修改

### 3.2 判断条件说明

**有 register 方法?** - 检查工具文件中是否存在以下代码：

```python
@classmethod
def register(cls):
    """注册工具到全局注册表"""
    return BusinessToolRegistry.register_by_class(cls)
```

### 3.3 修改指南

#### 情况 A: 工具类有 register 方法

**修改前**:
```python
class XxxTool(BusinessTool[SiteT, ParamT]):
    name = "xxx"
    site_type = SiteT
    ...

    @classmethod
    def register(cls):
        """注册工具到全局注册表"""
        return BusinessToolRegistry.register_by_class(cls)
```

**修改后 - 方案 1: 使用装饰器** (推荐)
```python
@business_tool(name="xxx", site_type=XiaohongshuSite, operation_category="login")
class XxxTool(BusinessTool[XiaohongshuSite, ParamT]):
    name = "xxx"  # 可省略，由装饰器设置
    description = "..."
    ...

    # 无需 register 方法
```

**修改后 - 方案 2: 保留类属性 + 移除方法**
```python
class XxxTool(BusinessTool[SiteT, ParamT]):
    name = "xxx"
    site_type = SiteT
    auto_register = True  # 标记自动注册
    ...
    # 无需 register 方法
```

#### 情况 B: 模块 __init__.py 手动注册

**修改前**:
```python
def register():
    """注册所有登录相关工具"""
    from src.tools.business.registry import BusinessToolRegistry

    count = 0
    if BusinessToolRegistry.register_by_class(LoginTool1):
        count += 1
    if BusinessToolRegistry.register_by_class(LoginTool2):
        count += 1
    if BusinessToolRegistry.register_by_class(LoginTool3):
        count += 1
    return count
```

**修改后**:
```python
def register():
    """注册所有登录相关工具（自动发现）"""
    import sys
    from src.tools.business import BusinessToolRegistry

    # 从当前模块自动发现 BusinessTool 子类
    return BusinessToolRegistry.discover_from_module(
        sys.modules[__name__],
        prefix="xhs_"  # 根据站点调整
    )
```

---

## 四、实施顺序

### 阶段 1: 基础设施准备

1. 确认 `discover_and_register` 函数可用
2. 可选：创建 `@business_tool` 装饰器（如果决定使用装饰器方案）

### 阶段 2: 小红书工具迁移（16 个）

顺序建议：按模块依次处理
1. login (4 个)
2. browse (4 个)
3. interact (4 个)
4. publish (4 个)

### 阶段 3: 闲鱼工具迁移（2 个）

1. login (1 个)
2. publish (1 个)

### 阶段 4: 模块注册简化（6 个）

与工具迁移同步进行

### 阶段 5: 测试验证

1. 执行 `pytest tests_api.py`
2. 执行 `pytest tests_xiaohongshu.py`
3. 检查工具列表输出

---

## 五、确认方案

### 方案选择

| 方案 | 优点 | 缺点 |
|------|------|------|
| **A: 装饰器自动注册** | 代码最简洁、自动注册 | 需要定义装饰器 |
| **B: auto_register 标记** | 简单实现、利用现有 discover | 需要启用 discover |
| **C: 保留现有 + 简化模块** | 无需改工具类 | 仍需手动维护 register |

### 待确认问题

1. **采用哪个方案?**
   - A: 装饰器自动注册（推荐）
   - B: auto_register 标记
   - C: 仅简化模块注册

2. **是否需要迁移已有工具?**
   - 是：移除所有 register 方法
   - 否：仅简化模块注册，保留工具类中的 register

3. **如何处理 name 前缀?**
   - 小红书: `xhs_` 前缀
   - 闲鱼: `xianyu_` 前缀

---

## 六、风险与回滚

### 风险识别

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 工具未注册 | 工具无法使用 | 先测试后提交 |
| discover 匹配失败 | 部分工具漏注册 | 检查类名规范 |
| 依赖导入失败 | 模块加载错误 | 检查 import 路径 |

### 回滚方案

如需回滚到当前模式：
1. 恢复工具类的 register 方法
2. 恢复模块 __init__.py 的手动注册
3. 撤销 discover 调用的修改

---

## 七、检查清单

### 代码修改检查

- [ ] 工具类移除 register 方法或添加装饰器
- [ ] 模块 __init__.py 改为 discover_from_module
- [ ] import 语句正确（sys.modules[__name__]）
- [ ] prefix 参数与站点匹配

### 测试验证检查

- [ ] pytest tests_api.py 通过
- [ ] pytest tests_xiaohongshu.py 通过
- [ ] 工具列表包含所有 18 个工具
- [ ] 工具可正常执行

---

*文档结束*

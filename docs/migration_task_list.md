# 业务工具直接模式迁移任务清单

> 生成日期: 2026-03-04
> 目标: 将所有业务工具迁移到直接模式（直接使用 context.client + ensure_site_tab），完全移除间接模式

---

## 一、架构理解

### 执行模式定义

| 模式 | 代码特征 | 优点 | 缺点 |
|------|----------|------|------|
| **直接模式** | `client = context.client` + `ensure_site_tab()` | 标签页复用、多浏览器隔离 | 需添加类属性 |
| **间接模式** | `await site.xxx()` | 代码简洁 | 每次创建新标签页、跨浏览器风险 |

### 基类能力（已实现）

`BusinessTool` 基类提供 `ensure_site_tab()` 方法，子类只需添加：

```python
class XxxTool(BusinessTool[SiteT, ParamsT]):
    target_site_domain = "example.com"      # 启用自动 tab 管理
    default_navigate_url = "https://example.com"
```

---

## 二、任务分类汇总

### 类别 A: ✅ 已完成（无需操作）

| # | 站点 | 文件 | 状态 |
|---|------|------|------|
| 1 | 小红书 | `login/check_login_status.py` | ✅ 已使用 ensure_site_tab |
| 2 | 小红书 | `login/get_login_qrcode.py` | ✅ 已使用 ensure_site_tab |

### 类别 B: ⬜ 需重构（有手动 tab 管理代码）

| # | 站点 | 文件 | 问题代码行 | 变更内容 |
|---|------|------|-------------|----------|
| 1 | 小红书 | `browse/list_feeds.py` | 97-163 | 替换为 ensure_site_tab() 调用 |
| 2 | 闲鱼 | `login/get_cookies.py` | ~86-117 | 替换为 ensure_site_tab() 调用 |

### 类别 C: ❌ 间接模式（需全面重构为直接模式）

#### C1: 小红书 - interact 类

| # | 文件 | 当前模式 | 建议 |
|---|------|----------|------|
| 1 | `interact/like_feed.py` | `await site.like_feed()` | 改为直接 client 操作 |
| 2 | `interact/favorite_feed.py` | `await site.favorite_feed()` | 改为直接 client 操作 |
| 3 | `interact/post_comment.py` | `await site.post_comment()` | 改为直接 client 操作 |
| 4 | `interact/reply_comment.py` | `await site.reply_comment()` | 改为直接 client 操作 |

#### C2: 小红书 - publish 类

| # | 文件 | 当前模式 | 建议 |
|---|------|----------|------|
| 1 | `publish/publish_content.py` | `await site.publish_content()` | 改为直接 client 操作 |
| 2 | `publish/publish_video.py` | `await site.publish_video()` | 改为直接 client 操作 |
| 3 | `publish/schedule_publish.py` | `await site.schedule_publish()` | 改为直接 client 操作 |
| 4 | `publish/check_publish_status.py` | `await site.check_publish_status()` | 改为直接 client 操作 |

#### C3: 小红书 - browse 类

| # | 文件 | 当前模式 | 建议 |
|---|------|----------|------|
| 1 | `browse/user_profile.py` | `await site.extract_data()` | 改为直接 client 操作 |
| 2 | `browse/get_feed_detail.py` | `await site.extract_data()` | 改为直接 client 操作 |
| 3 | `browse/search_feeds.py` | `await site.search()` | 改为直接 client 操作 |

#### C4: 小红书 - login 类

| # | 文件 | 当前模式 | 建议 |
|---|------|----------|------|
| 1 | `login/wait_login.py` | `await site.check_login_status()` | 改为直接 client 操作 |
| 2 | `login/delete_cookies.py` | `await site.delete_cookies()` | 改为直接 client 操作 |

#### C5: 闲鱼 - publish 类

| # | 文件 | 当前模式 | 建议 |
|---|------|----------|------|
| 1 | `publish/publish_item.py` | `await site.publish_item()` | 改为直接 client 操作 |

---

## 三、迁移方案

### 3.1 类别 B：手动 tab 管理 → ensure_site_tab

#### 文件: list_feeds.py (小红书)

**当前问题代码** (97-163行):
```python
# 手动 tab 管理 - 约 70 行重复代码
tab_id = params.tab_id
if not tab_id:
    tab_id = context.tab_id
if not tab_id and hasattr(client, 'get_site_tab'):
    tab_id = client.get_site_tab(site_domain, secret_key)
    # ... 有效性检测 ...
if not tab_id:
    # 获取活动标签页 ...
if not tab_id:
    # 创建新标签页 ...
```

**迁移后代码**:
```python
class ListFeedsTool(BusinessTool[...]):
    # 类属性已存在
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/"

    async def _execute_core(self, params, context, site):
        client = context.client
        # 使用基类的 ensure_site_tab 方法
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url=self._get_page_url(params.page_type),
            param_tab_id=params.tab_id
        )
        if not tab_id:
            return XHSListFeedsResult(success=False, message="无法获取标签页")
```

#### 文件: get_cookies.py (闲鱼)

**待添加类属性**:
```python
class GetCookiesTool(BusinessTool[...]):
    target_site_domain = "goofish.com"
    default_navigate_url = "https://www.goofish.com"
```

**替换手动 tab 管理代码为 ensure_site_tab 调用**。

---

### 3.2 类别 C：间接模式 → 直接模式

#### 迁移模板

**当前代码** (间接模式):
```python
async def _execute_core(self, params, context, site):
    # 调用网站适配器
    result = await site.xxx(context, param1=xxx)
    return XxxResult(...)
```

**目标代码** (直接模式):
```python
class XxxTool(BusinessTool[...]):
    target_site_domain = "xiaohongshu.com"
    default_navigate_url = "https://www.xiaohongshu.com/"

    async def _execute_core(self, params, context, site):
        client = context.client
        if not client:
            return XxxResult(success=False, message="无法获取浏览器客户端")

        # 使用 ensure_site_tab 获取有效标签页
        tab_id = await self.ensure_site_tab(
            client=client,
            context=context,
            fallback_url=xxx,  # 根据工具确定
            param_tab_id=params.tab_id
        )

        if not tab_id:
            return XxxResult(success=False, message="无法获取标签页")

        # 直接执行浏览器操作（复制 site 适配器的核心逻辑）
        result = await client.execute_tool("xxx", {...}, tabId=tab_id)
        # ... 处理结果 ...
```

#### 详细迁移说明

**关键点**：

1. **添加类属性**：
   - `target_site_domain`: 网站域名
   - `default_navigate_url`: 默认导航 URL

2. **获取 client**：
   ```python
   client = context.client
   if not client:
       return XxxResult(success=False, message="无法获取浏览器客户端")
   ```

3. **获取 tab_id**：
   ```python
   tab_id = await self.ensure_site_tab(
       client=client,
       context=context,
       fallback_url="默认URL",
       param_tab_id=params.tab_id
   )
   ```

4. **直接执行操作**：
   - 查看 `adapters.py` 中 site 方法的实现
   - 将核心浏览器操作逻辑复制到工具中
   - 使用 `client.execute_tool()` 直接执行

5. **处理结果**：
   - 将 site 返回的 Result 转换为工具的 Result

---

## 四、验收标准

### 4.1 代码检查清单

- [ ] 所有工具都有 `target_site_domain` 类属性
- [ ] 所有工具都有 `default_navigate_url` 类属性
- [ ] 无 `await site.xxx()` 调用模式
- [ ] 所有浏览器操作通过 `context.client` 执行
- [ ] 使用 `ensure_site_tab()` 获取标签页

### 4.2 测试验证

```bash
# API 测试
pytest tests_api.py

# RPA 测试
pytest tests_xiaohongshu.py

# 特定工具测试
pytest tests_xiaohongshu.py::test_list_feeds
pytest tests_xiaohongshu.py::test_like_feed
```

### 4.3 多浏览器隔离测试

验证场景：
1. 同时控制浏览器 A (secret_key="abc") 和浏览器 B (secret_key="def")
2. 浏览器 A 执行操作后，检查 tab_id 是否属于浏览器 A
3. 确认无跨浏览器操作

---

## 五、任务执行顺序

### 阶段 1：类别 B（手动 tab 管理）— 高优先级

1. ⬜ `list_feeds.py` - 已有类属性，替换手动代码
2. ⬜ `get_cookies.py` - 添加类属性，替换手动代码

### 阶段 2：类别 C（间接模式）- 中优先级

#### 2.1 小红书 interact 类
3. ❌ `like_feed.py`
4. ❌ `favorite_feed.py`
5. ❌ `post_comment.py`
6. ❌ `reply_comment.py`

#### 2.2 小红书 publish 类
7. ❌ `publish_content.py`
8. ❌ `publish_video.py`
9. ❌ `schedule_publish.py`
10. ❌ `check_publish_status.py`

#### 2.3 小红书 browse 类
11. ❌ `user_profile.py`
12. ❌ `get_feed_detail.py`
13. ❌ `search_feeds.py`

#### 2.4 小红书 login 类
14. ❌ `wait_login.py`
15. ❌ `delete_cookies.py`

#### 2.5 闲鱼
16. ❌ `publish_item.py`

---

## 六、风险与回滚

### 风险识别

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| site 适配器方法变更 | 工具与适配器逻辑不一致 | 同步更新适配器方法 |
| 选择器失效 | DOM 操作失败 | 保留多选择器遍历逻辑 |
| 登录状态变化 | 需要重新登录 | 添加登录检测逻辑 |

### 回滚方案

如需回滚到间接模式：
1. 移除 `target_site_domain` 和 `default_navigate_url` 类属性
2. 恢复 `await site.xxx()` 调用
3. 移除 `ensure_site_tab()` 调用

---

## 七、待移除代码（迁移完成后）

迁移完成后，以下代码可以移除：

1. **`src/tools/business/site_base.py`** 中的间接方法定义（可选保留作为后备）
2. **`adapters.py`** 中的业务方法（可选保留作为后备）

**注意**：建议保留 adapters 方法作为后备，暂不删除。

---

## 八、总结

| 类别 | 数量 | 状态 |
|------|------|------|
| A: 已完成 | 2 | ✅ |
| B: 需重构 | 2 | ⬜ |
| C: 需全面重构 | 15 | ❌ |
| **总计** | **19** | |

**目标**：所有 19 个工具均使用直接模式，实现标签页复用和多浏览器隔离。

---

*文档结束*

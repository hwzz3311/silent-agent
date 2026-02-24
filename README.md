# SilentAgent - 浏览器智能代理控制系统

## 项目概述

SilentAgent 是一个 **Chrome 扩展 + Python 控制器** 系统，通过 `chrome.scripting` API + WebSocket 工具调用协议实现远程浏览器自动化控制。

**核心优势：无需 CDP 端口、无调试器横幅、无 `navigator.webdriver` 标志，通过脚本注入实现对任意授权网站的远程操作。**

## 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                       SilentAgent 架构 v2                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐   chrome.scripting   ┌──────────────────────┐    │
│  │   Chrome     │◄────────────────────│   Chrome 扩展        │    │
│  │   Browser    │   executeScript()    │  (background.js)     │    │
│  │  (任意标签)   │                      │  12 个内置工具        │    │
│  └──────────────┘                      └──────────┬───────────┘    │
│                                                    │                │
│                                        WebSocket   │  /extension    │
│                                                    ▼                │
│                                        ┌──────────────────────┐    │
│                                        │   Python Relay       │    │
│                                        │   Server             │    │
│                                        │   :18792             │    │
│                                        └──────────┬───────────┘    │
│                                        WebSocket   │  /controller   │
│                                                    ▼                │
│                                        ┌──────────────────────┐    │
│                                        │   Python 控制器      │    │
│                                        │  (SilentAgentClient) │    │
│                                        │   + AI / 业务逻辑    │    │
│                                        │   + REST API 服务    │    │
│                                        └──────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

通信流程:
  控制器 → Relay:  { method:"executeTool", params:{ name, args } }
  Relay  → 扩展:   { type:"tool_call", requestId, payload:{ name, args } }
  扩展   → 页面:   chrome.scripting.executeScript(...)
  扩展   → Relay:  { type:"tool_result", requestId, result }
  Relay  → 控制器: { id, result }
```

## 核心特性

### 1. 工具化操作
- 12 个内置工具覆盖导航、点击、填充、提取、截图、滚动等常见场景
- 支持通过 `inject_script` 远程下发任意 JS 到页面执行
- Python 端可自由组合工具调用，无需修改扩展代码即可实现任意业务逻辑

### 2. 高兼容性
- 使用 `chrome.scripting` API，不依赖 `chrome.debugger`
- 不受其他浏览器扩展干扰（旧版 debugger 方案的核心痛点）
- 支持所有常规网页，通过权限管理授权目标网站

### 3. 本地优先 (Local First)
- 数据完全由本地 Python 控制
- Relay 服务器运行在 localhost
- 无云端依赖，可离线运行

### 4. 隐蔽性
- 无 `navigator.webdriver` 标志
- 无 Chrome 调试器横幅（"... is debugging this tab"）
- 无 CDP 端口暴露

### 5. 业务抽象层
- **业务工具框架**: 基于 `Tool` 抽象基类的工具开发框架
- **站点适配器**: 支持多站点适配 (`Site` 抽象基类)
- **流程引擎**: 支持流程定义和执行
- **录制回放**: 操作录制和回放功能
- **REST API**: 提供 HTTP API 接口

## 内置工具列表

### 浏览器基础工具 (`src/tools/browser/`)

| 工具名 | 功能 | 文件 |
|--------|------|------|
| `browser.navigate` | 导航到 URL | `navigate.py` |
| `browser.click` | 点击页面元素 | `click.py` |
| `browser.fill` | 填充表单输入 | `fill.py` |
| `browser.extract` | 从 DOM/window/document 提取数据 | `extract.py` |
| `browser.screenshot` | 页面截图 | `screenshot.py` |
| `browser.scroll` | 滚动页面 | `scroll.py` |
| `browser.inject` | 注入执行脚本 | `inject.py` |
| `browser.evaluate` | 执行 JavaScript | `evaluate.py` |
| `browser.wait` | 等待元素出现 | `wait.py` |
| `browser.keyboard` | 模拟键盘输入 | `keyboard.py` |
| `browser.a11y_tree` | 无障碍树操作 | `a11y_tree.py` |
| `browser.control` | 浏览器控制（Cookie 管理等） | `control.py` |

### 业务工具框架 (`src/tools/`)

| 模块 | 说明 |
|------|------|
| `base.py` | `Tool` 抽象基类，`ToolParameters` 参数类 |
| `registry.py` | 工具注册表 |
| `business/` | 业务抽象层 |
| `business/site_base.py` | `Site` 站点适配器抽象基类 |
| `business/registry.py` | 业务工具注册表 |
| `business/errors.py` | 业务错误定义 |

### 小红书站点适配器 (`src/tools/sites/xiaohongshu/`)

| 组件 | 说明 |
|------|------|
| `adapters.py` | `XiaohongshuSite` 适配器 |
| `selectors.py` | 小红书特定选择器 |
| `utils/` | 底层工具目录（迁移自 `xhs/`） |
| `tools/` | 业务工具目录 |
| `tools/login/` | 登录相关工具 |
| `tools/publish/` | 发布相关工具 |
| `tools/browse/` | 浏览相关工具 |
| `tools/interact/` | 互动相关工具 |
| `publishers/` | 发布流程编排器 |

#### utils 工具模块

| 工具 | 功能 | 文件 |
|------|------|------|
| `ReadPageDataTool` | 读取页面数据 | `page_data.py` |
| `InjectScriptTool` | 脚本注入执行 | `inject_script.py` |
| `VideoDownloadTool` | 视频下载 | `video_download.py` |
| `VideoChunkTransferTool` | 视频分块传输 | `video_transfer.py` |
| `VideoUploadInterceptTool` | 上传拦截 | `video_intercept.py` |
| `UploadFileTool` | 单文件上传 | `file_upload.py` |
| `SetFilesTool` | 多文件设置 | `file_upload.py` |

#### 业务工具

| 工具 | 功能 | 目录 |
|------|------|------|
| `xhs_check_login_status` | 检查登录状态 | `tools/login/` |
| `xhs_get_login_qrcode` | 获取登录二维码 | `tools/login/` |
| `xhs_wait_login` | 等待登录完成 | `tools/login/` |
| `xhs_delete_cookies` | 删除 Cookie | `tools/login/` |
| `xhs_publish` | 发布流程编排 | `publishers/` |
| `xhs_publish_content` | 发布图文 | `tools/publish/` |
| `xhs_publish_video` | 发布视频 | `tools/publish/` |
| `xhs_list_feeds` | 获取笔记列表 | `tools/browse/` |
| `xhs_search_feeds` | 搜索笔记 | `tools/browse/` |
| `xhs_get_feed_detail` | 获取笔记详情 | `tools/browse/` |
| `xhs_get_user_profile` | 获取用户主页 | `tools/browse/` |
| `xhs_like_feed` | 点赞笔记 | `tools/interact/` |
| `xhs_favorite_feed` | 收藏笔记 | `tools/interact/` |
| `xhs_post_comment` | 发表评论 | `tools/interact/` |
| `xhs_reply_comment` | 回复评论 | `tools/interact/` |

### 流程引擎 (`src/flows/`)

| 模块 | 说明 |
|------|------|
| `engine.py` | 流程执行引擎 |
| `context.py` | 流程执行上下文 |
| `steps/` | 流程步骤类型 |
| `steps/base.py` | 步骤基类 |
| `steps/action.py` | 动作步骤 |
| `steps/condition.py` | 条件步骤 |
| `steps/loop.py` | 循环步骤 |
| `steps/wait.py` | 等待步骤 |
| `parsers/` | 流程解析器 |
| `parsers/json.py` | JSON 格式解析器 |

### 录制回放 (`src/recorder/`)

| 模块 | 说明 |
|------|------|
| `storage.py` | 录制存储 |
| `adapter.py` | 选择器适配器 |
| `player.py` | 回放播放器 |
| `optimizer.py` | 录制优化器 |

### API 服务 (`src/api/`)

| 模块 | 说明 |
|------|------|
| `app.py` | FastAPI 应用入口 |
| `routes/` | API 路由 |
| `routes/tools.py` | 工具相关接口 |
| `routes/execute.py` | 执行相关接口 |
| `routes/flows.py` | 流程相关接口 |
| `routes/record.py` | 录制回放接口 |
| `schemas/` | 数据模型 |
| `schemas/common.py` | 通用模型 |
| `schemas/tools.py` | 工具相关模型 |
| `schemas/execute.py` | 执行相关模型 |
| `schemas/flows.py` | 流程相关模型 |
| `schemas/record.py` | 录制相关模型 |

## 项目结构

```
network_hook/
├── extension/                      # Chrome 扩展
│   ├── manifest.json              # 扩展配置 (Manifest V3)
│   ├── background.js              # 主逻辑（工具注册表 + WebSocket 客户端）
│   ├── options.html               # 设置页面（端口配置 + 权限管理）
│   ├── options.js                 # 设置页面脚本
│   └── icons/                     # 扩展图标
│
├── src/                           # Python 控制器 ⭐ (新结构)
│   ├── relay_server.py            # WebSocket Relay 服务器
│   ├── relay_client.py            # 控制器客户端（便捷 API）
│   ├── cdp_client.py              # 直连 CDP 客户端（备用，旧版）
│   ├── neuron.py                  # Native Messaging Host（旧版）
│   ├── demo.py                    # 直连 CDP 演示（旧版）
│   │
│   ├── api/                       # REST API 服务 ⭐
│   │   ├── app.py                 # FastAPI 应用入口
│   │   ├── routes/                # API 路由
│   │   │   ├── tools.py           # /api/v1/tools
│   │   │   ├── execute.py         # /api/v1/execute
│   │   │   ├── flows.py           # /api/v1/flows
│   │   │   └── record.py          # /api/v1/record
│   │   └── schemas/               # 数据模型
│   │
│   ├── tools/                     # 工具框架 ⭐
│   │   ├── base.py                # Tool 抽象基类
│   │   ├── registry.py            # 工具注册表
│   │   ├── browser/               # 浏览器基础工具
│   │   │   ├── click.py           # 点击
│   │   │   ├── fill.py            # 填充
│   │   │   ├── navigate.py        # 导航
│   │   │   ├── extract.py         # 提取
│   │   │   ├── screenshot.py      # 截图
│   │   │   └── ...                # 其他工具
│   │   └── business/              # 业务抽象层
│   │       ├── site_base.py       # Site 站点适配器基类
│   │       ├── registry.py        # 业务工具注册表
│   │       ├── errors.py          # 业务错误
│   │       └── sites/             # 站点适配器
│   │           └── xiaohongshu/   # 小红书适配器
│   │               ├── adapters.py
│   │               ├── selectors.py
│   │               ├── utils/     # 底层工具（迁移自 xhs/）
│   │               ├── tools/     # 业务工具
│   │               │   ├── login/
│   │               │   ├── publish/
│   │               │   ├── browse/
│   │               │   └── interact/
│   │               └── publishers/ # 流程编排器
│   │
│   ├── flows/                     # 流程引擎 ⭐
│   │   ├── engine.py              # 执行引擎
│   │   ├── context.py             # 执行上下文
│   │   ├── steps/                 # 步骤类型
│   │   └── parsers/               # 解析器
│   │
│   ├── recorder/                  # 录制回放 ⭐
│   │   ├── storage.py             # 存储
│   │   ├── adapter.py             # 选择器适配
│   │   ├── player.py              # 播放器
│   │   └── optimizer.py           # 优化器
│   │
│   ├── client/                    # 客户端 ⭐
│   │   ├── client.py              # SilentAgentClient
│   │   ├── connection.py          # 连接管理
│   │   └── exceptions.py          # 异常定义
│   │
│   ├── core/                      # 核心模块
│   │   ├── result.py              # 结果定义
│   │   └── context.py             # 上下文
│   │
│   └── logger/                    # 日志系统
│       ├── config.py              # 配置
│       ├── formatters.py          # 格式化器
│       └── handlers.py            # 处理器
│
├── xiaohongshu-mcp-extension-latest/  # 参考项目（竞品分析）
│
├── todos.md                       # 项目任务清单
├── todos_v2.md                    # 迁移计划
├── todos_v3.md                    # API 服务开发计划
├── todos_v4.md                    # xhs 工具迁移计划
└── README.md
```

## 快速开始

### 前置条件

```bash
pip install -r requirements.txt
```

主要依赖：
- `websockets` - WebSocket 通信
- `fastapi` - REST API 服务
- `uvicorn` - ASGI 服务器
- `pydantic` - 数据验证
- `pyyaml` - YAML 解析

### 1. 启动 Relay 服务器

```bash
# 基础启动
python src/relay_server.py

# 指定端口
python src/relay_server.py --port 18792

# 详细日志
python src/relay_server.py --port 18792 --log-level DEBUG
```

### 2. 启动 API 服务（可选）

```bash
# 启动 REST API 服务
uvicorn src.api.app:app --host 0.0.0.0 --port 8080 --reload
```

API 端点：
- `GET /health` - 健康检查
- `GET /api/v1/tools` - 工具列表
- `POST /api/v1/execute` - 执行工具
- `GET /api/v1/flows` - 流程列表
- `POST /api/v1/record/start` - 开始录制

### 3. 加载 Chrome 扩展

1. 打开 `chrome://extensions/`
2. 启用「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择 `network_hook/extension` 目录

### 4. 授权网站权限

1. 点击扩展图标 → 设置页面
2. 在「网站权限」区域：
   - **授权所有网站**：点击「授权所有网站」按钮（开发阶段推荐）
   - **逐个添加**：输入域名（如 `baidu.com`），点击「添加」
   - **快速添加**：点击常用网站预设标签

### 5. 使用 Python 控制

#### 方式一：使用 SilentAgentClient

```python
import asyncio
from src.client.client import SilentAgentClient

async def main():
    async with SilentAgentClient(host="127.0.0.1", port=18792) as client:
        await client.wait_for_extension(timeout=30)
        print(f"可用工具: {client.tools}")

        # 导航到网页
        await client.navigate("https://www.baidu.com")

        # 获取页面信息
        info = await client.get_page_info()
        print(f"页面: {info}")

asyncio.run(main())
```

#### 方式二：使用业务工具

```python
from src.tools.sites.xiaohongshu import XiaohongshuSite

async def main():
    site = XiaohongshuSite()

    # 检查登录状态
    login_status = await site.check_login_status()
    print(f"登录状态: {login_status}")

    # 发布图文笔记
    result = await site.publish_content(
        title="测试标题",
        content="测试内容",
        images=[],
        topic_tags=["测试标签"]
    )
    print(f"发布结果: {result}")

asyncio.run(main())
```

## 小红书工具使用示例

### 登录相关

```python
from src.tools.sites.xiaohongshu.tools.login import (
    get_login_qrcode,
    wait_login,
    delete_cookies,
)

# 获取登录二维码
qrcode = await get_login_qrcode()
print(f"二维码URL: {qrcode.data.qrcode_url}")

# 等待登录
await wait_login(timeout=120)

# 删除 Cookie（退出登录）
await delete_cookies()
```

### 发布相关

```python
from src.tools.sites.xiaohongshu import XiaohongshuPublisher

# 使用发布流程编排器
publisher = XiaohongshuPublisher()

# 发布图文笔记
result = await publisher.publish_note(
    title="我的第一条笔记",
    content="这是一篇测试笔记的内容",
    images=[
        {"base64Data": "...", "fileName": "image1.jpg", "mimeType": "image/jpeg"}
    ],
    topics=["测试", "RPA"]
)
```

### 浏览相关

```python
from src.tools.sites.xiaohongshu.tools.browse import (
    list_feeds,
    search_feeds,
    get_feed_detail,
    get_user_profile,
)

# 获取笔记列表
feeds = await list_feeds(max_items=10)

# 搜索笔记
results = await search_feeds(keyword="RPA", max_items=20)

# 获取笔记详情
detail = await get_feed_detail(note_id="xxx")

# 获取用户主页
profile = await get_user_profile(user_id="xxx")
```

### 互动相关

```python
from src.tools.sites.xiaohongshu.tools.interact import (
    like_feed,
    favorite_feed,
    post_comment,
    reply_comment,
)

# 点赞
await like_feed(note_id="xxx")

# 收藏
await favorite_feed(note_id="xxx", folder_name="收藏夹")

# 发表评论
await post_comment(note_id="xxx", content="写的很好！")

# 回复评论
await reply_comment(comment_id="yyy", content="同意！")
```

## 工具注册与使用

### 注册业务工具

```python
from src.tools.business.registry import BusinessToolRegistry
from src.tools.sites.xiaohongshu.tools.login import register as login_register
from src.tools.sites.xiaohongshu.tools.publish import register as publish_register

# 注册小红书工具
from src.tools.sites.xiaohongshu import XiaohongshuSite

# 注册所有小红书工具
from src.tools.sites.xiaohongshu import register_xhs_tools
register_xhs_tools()

# 或手动注册各类工具
login_register()      # 登录工具
publish_register()    # 发布工具
browse_register()     # 浏览工具
interact_register()   # 互动工具

# 获取已注册工具
tools = BusinessToolRegistry.get_by_site(XiaohongshuSite)
```

### 使用工具

```python
from src.tools.registry import tool_registry

# 通过名称获取工具
tool = tool_registry.get("xhs_check_login_status")
if tool:
    result = await tool.execute(params, context)
```

## 流程定义示例

```python
from src.flows.parsers.json import JsonFlowParser

flow_data = {
    "name": "自动发布流程",
    "variables": [
        {"name": "title", "type": "string", "required": True},
        {"name": "content", "type": "string", "required": True},
    ],
    "steps": [
        {
            "id": "step1",
            "name": "检查登录状态",
            "type": "action",
            "tool": "xhs_check_login_status",
        },
        {
            "id": "step2",
            "name": "发布笔记",
            "type": "action",
            "tool": "xhs_publish",
            "params": {
                "title": "${title}",
                "content": "${content}",
            },
        },
    ],
}

parser = JsonFlowParser()
flow = parser.parse(flow_data)

# 执行流程
from src.flows.engine import FlowEngine
engine = FlowEngine()
result = await engine.execute(flow, context)
```

## 录制回放

```python
from src.recorder import RecordingStorage, RecordingPlayer

# 开始录制
from src.api.routes.record import start_recording
result = await start_recording(tab_id=None)

# 执行操作...

# 停止录制
from src.api.routes.record import stop_recording
recording = await stop_recording(recording_id=result.recording_id)

# 回放
from src.api.routes.record import replay_recording
replay_result = await replay_recording(
    recording_id=recording.recording_id,
    speed=1.5
)
```

## API 健康检查

```bash
# Relay 服务器
curl http://127.0.0.1:18792/health

# REST API 服务
curl http://127.0.0.1:8080/health
```

预期响应：
```json
// Relay
{
  "status": "healthy",
  "extension_connected": true,
  "tools_count": 12
}

// REST API
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## 状态指示器

| Badge | 含义 |
|-------|------|
| **ON** (绿色) | 已连接到 Relay 服务器 |
| **…** (黄色) | 正在连接 |
| **!** (红色) | 连接失败（Relay 未运行） |
| (空) | 未连接 |

## 通信协议

### 扩展 → Relay

```json
// 连接握手
{"type": "hello", "extensionId": "xxx", "version": "2.0.0", "tools": ["inject_script", "chrome_navigate", ...]}

// 工具执行结果
{"type": "tool_result", "requestId": "abc123", "result": {"content": [{"type": "text", "text": "..."}]}}

// 心跳响应
{"type": "pong"}
```

### Relay → 扩展

```json
// 工具调用请求
{"type": "tool_call", "requestId": "abc123", "payload": {"name": "chrome_click", "args": {"selector": "#btn"}}}

// 心跳
{"type": "ping"}
```

### 控制器 → Relay

```json
// 执行工具
{"id": 1, "method": "executeTool", "params": {"name": "chrome_navigate", "args": {"url": "https://example.com"}}}

// 列出工具
{"id": 2, "method": "listTools"}

// 获取状态
{"id": 3, "method": "getStatus"}
```

### Relay → 控制器

```json
// 成功响应
{"id": 1, "result": {"content": [{"type": "text", "text": "{...}"}]}}

// 错误响应
{"id": 1, "error": "扩展未连接"}

// 事件推送
{"method": "event", "params": {"type": "extension_connected", "tools": [...]}}
```

## 安全性与风险

### 优势（相比 Selenium/Puppeteer/CDP）

| 维度 | Selenium/Puppeteer | chrome.debugger (旧版) | chrome.scripting (当前) |
|------|-------------------|----------------------|------------------------|
| `navigator.webdriver` | `true` (易检测) | 无 | 无 |
| 调试器横幅 | 无 (但有其他指纹) | 有黄色提示栏 | **无** |
| CDP 端口暴露 | 有 | 有 | **无** |
| 浏览器指纹 | headless 特征多 | 正常浏览器 | **正常浏览器** |
| 其他扩展干扰 | 不影响 | **会冲突** | 不影响 |

### 已知风险点

#### 1. `isTrusted` 检测（中风险）

通过 `chrome.scripting` 执行的 `.click()` 或 `dispatchEvent()` 产生的事件，`isTrusted` 属性为 `false`。

**缓解方案**：如需 `isTrusted=true` 的事件，可通过以下方式：
- `chrome.debugger` + `Input.dispatchMouseEvent`（会有调试栏）
- Native Messaging + OS 级输入模拟（macOS `CGEvent` / Windows `SendInput`）

#### 2. 行为指纹（低风险）

- 点击前缺少 `mousemove` 轨迹
- 输入速度可能过于均匀
- 操作时序可能不够自然

**缓解方案**：在 Python 端添加随机延迟和操作间隔。

#### 3. 扩展特征（极低风险）

- `chrome.scripting.executeScript` 注入的代码本身不会在页面留下持久痕迹
- ISOLATED world 的脚本完全对页面隐藏
- MAIN world 的脚本是一次性执行，无固定全局变量

### 风险等级总结

| 目标网站类型 | 风险等级 | 说明 |
|-------------|---------|------|
| 普通网站 | 极低 | 基本不会被检测 |
| 社交平台（小红书、微博等） | 低 | 通常不检查 `isTrusted` |
| 电商平台（淘宝、京东等） | 中低 | 部分操作可能有频率限制 |
| 验证码/支付页面 | 中高 | 可能检查 `isTrusted` 或行为指纹 |
| 强反爬网站（如 Cloudflare 防护） | 高 | 建议配合更底层的模拟方案 |

## 技术栈

- **Chrome 扩展**: Manifest V3, `chrome.scripting` API, `chrome.tabs` API
- **Python**:
  - `websockets` - 异步 WebSocket 通信
  - `fastapi` - REST API 服务
  - `uvicorn` - ASGI 服务器
  - `pydantic` - 数据验证
  - `asyncio` - 异步编程
- **通信协议**: WebSocket, JSON-RPC 风格的工具调用

## 与 xiaohongshu-mcp 的对比

| 维度 | SilentAgent | xiaohongshu-mcp |
|------|---------|----------------|
| 页面操作方式 | `chrome.scripting.executeScript` | 相同 |
| 通信协议 | 工具调用 (TOOL_CALL/RESULT) | 相同模式 |
| 预置工具 | 12 个通用 + 15+ 业务专用 | 14 个 (含小红书专用) |
| 自定义逻辑 | Python 端 `inject_script` 下发 JS | 插件内预置 |
| 适用场景 | 通用浏览器自动化 + 多站点 | 小红书专用 |
| 服务端 | 本地 Relay (localhost) | 云端 WebSocket |
| 扩展方式 | Python 端封装，无需改插件 | 需修改插件源码 |
| 业务抽象层 | ✅ 完整支持 | ❌ |

## 更新日志

### 2026-02-15

- ✅ 完成 `src/api/schemas/` 模块重构
- ✅ 修复 `src/api/routes/` 导入问题
- ✅ 创建 `src/tools/browser/control.py`
- ✅ 创建 `src/recorder/optimizer.py`
- ✅ 完成小红书工具迁移到 `src/tools/sites/xiaohongshu/` 框架
  - `utils/` 目录：8 个底层工具迁移完成
  - `tools/` 目录：登录、发布、浏览、互动工具重构完成
  - `publishers/` 目录：`XiaohongshuPublisher` 重构完成

### 历史版本

请参见 [CHANGELOG.md](CHANGELOG.md)

## 注意事项

1. **权限授权**：首次使用需在设置页面授权目标网站的访问权限，否则 `chrome.scripting` 无法注入脚本
2. **启动顺序**：先启动 Relay 服务器，再点击扩展图标连接
3. **端口配置**：默认 18792，可在扩展设置页面修改
4. **Service Worker**：可在 `chrome://extensions/` → SilentAgent → 「Service Worker」查看扩展日志
5. **MAIN vs ISOLATED**：`inject_script` 的 `world` 参数决定脚本执行环境，MAIN 可访问页面 JS 变量，ISOLATED 更安全但只能操作 DOM

## 许可证

MIT License
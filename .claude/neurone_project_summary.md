# Neurone RPA 项目记忆

> 最后更新: 2026-02-13

## 项目概述

**Neurone** 是一个 Chrome 扩展 + Python 控制器的浏览器自动化系统，使用 `chrome.scripting` API + WebSocket 实现远程浏览器控制。

### 核心优势
- 无需 CDP 端口
- 无调试器横幅
- 无 `navigator.webdriver` 标志
- 高兼容性，不受其他扩展干扰

## 架构设计

```
Chrome Browser ←→ Chrome Extension ←→ Relay Server ←→ Python Controller
                   (background.js)      (:18792)         (SilentAgentClient)
```

## 项目结构

```
network_hook/
├── extension/                    # Chrome 扩展 (Manifest V3)
│   ├── background.js            # 主逻辑 (15+ 工具)
│   ├── cdp_adapter.js           # CDP 兼容层
│   ├── event_listener.js        # 事件监听器
│   └── manifest.json
│
├── src[src](../src)/                       # Python 控制器
│   ├── core/                    # 核心模块
│   │   ├── result.py            # Result[T] 统一返回结构
│   │   ├── context.py           # ExecutionContext
│   │   └── exceptions.py
│   │
│   ├── tools/                   # 工具工厂
│   │   ├── base.py              # Tool 抽象基类
│   │   ├── registry.py          # ToolRegistry
│   │   └── browser/             # 11个浏览器工具
│   │
│   ├── flows/                   # 流程引擎
│   │   ├── engine.py            # FlowEngine
│   │   ├── context.py           # FlowContext
│   │   └── steps/               # 步骤类型 (action/condition/loop/wait)
│   │
│   ├── api/                     # FastAPI 服务
│   │   ├── app.py
│   │   ├── routes/              # tools/execute/flows/record
│   │   └── schemas/             # Pydantic 模型
│   │
│   ├── client/                  # WebSocket 客户端
│   │   ├── client.py            # SilentAgentClient
│   │   ├── connection.py        # ConnectionManager
│   │   └── exceptions.py
│   │
│   ├── recorder/                # 录制回放
│   │   ├── storage.py           # RecordingStorage
│   │   ├── player.py            # RecordingPlayer
│   │   ├── adapter.py           # SelectorAdapter
│   │   └── optimizer.py         # RecordingOptimizer
│   │
│   ├── logger/                  # 日志系统
│   │   ├── config.py            # LogConfig
│   │   ├── formatters.py
│   │   ├── handlers.py
│   │   └── execution.py         # ExecutionLogger
│   │
│   └── relay_server.py          # Relay 服务器
│
├── README.md                     # 项目文档
└── todos.md                      # 开发任务清单
```

## 工具清单

### 扩展端工具 (15+)
| 工具名 | 功能 |
|--------|------|
| ClickTool | 点击元素 |
| FillTool | 填充表单 |
| NavigateTool | 导航 |
| KeyboardTool | 键盘输入 |
| WaitElementsTool | 等待元素 |
| ScreenshotTool | 截图 |
| ScrollTool | 滚动 |
| ExtractDataTool | 数据提取 |
| ReadPageDataTool | 读取页面数据 |
| InjectScriptTool | 注入脚本 |
| A11yTreeTool | 无障碍树 |
| CDPTool | CDP 命令 |
| RecorderTool | 录制回放 |

### Python 工具 (11个)
| 工具名 | 功能 |
|--------|------|
| browser.click | 点击元素 |
| browser.fill | 填充输入框 |
| browser.navigate | 导航到 URL |
| browser.keyboard | 键盘输入 |
| browser.wait | 等待条件 |
| browser.screenshot | 截图 |
| browser.scroll | 滚动页面 |
| browser.inject | 注入脚本 |
| browser.evaluate | 执行 JS |
| browser.extract | 提取数据 |
| browser.get_a11y_tree | 获取无障碍树 |

## 关键设计决策

### 1. 无 CDP 架构
- 使用 `chrome.scripting.executeScript` 替代 CDP
- 通过 WebSocket 发送工具调用
- 避免 CDP 端口暴露和调试横幅

### 2. 统一返回结构 Result[T]
```python
class Result[T]:
    success: bool
    data: T | None
    error: Error | None
    meta: ResultMeta
```

### 3. 工具抽象基类
```python
class Tool:
    name: str
    description: str

    async def execute(params, context) -> Result:
        ...
```

### 4. 执行上下文 ExecutionContext
- 变量作用域链
- Tab 会话管理
- 执行状态跟踪

### 5. 流程步骤类型
- ActionStep: 执行工具
- ConditionStep: 条件分支
- LoopStep: 循环执行
- WaitStep: 等待
- SetVarStep: 设置变量
- LogStep: 记录日志

## API 端点

### 工具接口
- `GET /api/v1/tools` - 列出所有工具
- `GET /api/v1/tools/{name}` - 获取工具详情
- `GET /api/v1/tools/{name}/schema` - 获取参数 Schema

### 执行接口
- `POST /api/v1/execute` - 执行工具调用
- `POST /api/v1/execute/batch` - 批量执行
- `POST /api/v1/execute/flow` - 执行流程

### 流程接口
- `GET /api/v1/flows` - 列出所有流程
- `POST /api/v1/flows` - 创建流程
- `GET /api/v1/flows/{id}` - 获取流程详情
- `POST /api/v1/flows/{id}/run` - 运行流程

### 录制接口
- `POST /api/v1/record/start` - 开始录制
- `POST /api/v1/record/{id}/stop` - 停止录制
- `GET /api/v1/record/{id}` - 获取录制
- `POST /api/v1/record/{id}/replay` - 回放录制

## 已完成任务 (2026-02-13)

### Phase 1: 浏览器插件端 ✅
- CDP 兼容层 (T1.1.1-T1.1.4)
- 模拟无障碍树 (T1.2.1-T1.2.5)
- 工具执行器 (T1.3.1-T1.3.3)
- 插件端录制回放 (T1.4.1-T1.4.4)

### Phase 2: Python 服务端 ✅
- 核心抽象层 (T2.2.1-T2.2.4)
- 工具工厂与注册表 (T2.3.1-T2.3.5)
- 流程引擎 (T2.4.1-T2.4.4)
- API 层 (T2.5.1-T2.5.5)
- WebSocket 客户端 (T2.6.1-T2.6.4)

### Phase 3: 录制/回放 ✅
- 录制系统 (T3.1.1-T3.1.4)
- 回放引擎 (T3.2.1-T3.2.4)
- AI 优化器 (T3.3.1-T3.3.3)

### Phase 4: 日志系统 ✅
- 日志架构 (T4.1.1-T4.1.3)
- 日志分析 (T4.2.1-T4.2.3)

## 待完成任务 (可选)

### T2.6.1: 连接池
- ConnectionManager 缺少连接池功能（目前单一连接）

### T5.x: 网站特定工具
- 小红书工具 (按用户要求暂不推进)

### T6.x: 测试与文档
- 单元测试、集成测试、端到端测试
- API 文档、开发文档、用户文档

## 技术栈

- **扩展端**: Manifest V3, `chrome.scripting`, `chrome.tabs`, WebSocket
- **Python**: `websockets`, `fastapi`, `pydantic`, `pyyaml`, `asyncio`

## 注意事项

1. 需要先启动 Relay 服务器，再连接扩展
2. 需要在扩展设置页面授权目标网站
3. `isTrusted` 属性为 false（脚本生成事件）
4. 默认端口 18792，可配置

## 启动命令

```bash
# 启动 Relay 服务器
cd python
python relay_server.py --port 18792

# 运行演示
python demo.py

# 运行测试
python -m pytest tests/ -v
```
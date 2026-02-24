# Neurone RPA 项目开发任务清单

> 基于 2026/2/11 技术评审会议确定的架构方向

## 项目整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Python 服务端层                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │   API 层    │ │  工具工厂   │ │  流程引擎   │ │  日志系统  │ │
│  │ FastAPI     │ │ ToolFactory │ │ FlowEngine  │ │ Logger     │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
│           │              │               │              │        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │  录制/回放  │ │  AI 优化器  │ │  工具注册表 │               │
│  │ Recorder    │ │ AIOptimizer │ │ ToolRegistry│               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                       浏览器插件端 (Extension)                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │  基础服务层  │ │ 工具执行器  │ │ 模拟无障碍树 │               │
│  │ BaseService │ │ ToolExecutor│ │ A11yTree    │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
│         │              │               │                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │ CDP 兼容层  │ │  录制回放   │ │  事件监听器 │               │
│  │ CDPAdapter  │ │ Recorder    │ │ EventListener│               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: 浏览器插件端 - 基础架构重构

### 1.1 CDP 兼容层实现

- [x] **T1.1.1**: 设计 CDP 基础命令接口抽象层 (`CDPAdapter`) - 已完成 ✅
  - 定义 CDP 命令标准接口：execute, evaluate, sendCommand, onEvent
  - 实现命令路由机制：将 CDP 命令分发到对应的处理器
  - 统一错误码体系：参考 CDP 规范定义错误类型

- [x] **T1.1.2**: 实现核心 CDP 命令兼容性 - 已完成 ✅
  - `Runtime.evaluate` → JS 脚本执行
  - `Runtime.callFunctionOn` → 函数调用
  - `DOM.getDocument` / `DOM.querySelector` → DOM 查询
  - `Page.addScriptToEvaluateOnNewDocument` → 页面注入

- [x] **T1.1.3**: 命令执行反馈机制 - 已完成 ✅
  - 响应数据结构设计：包含状态、数据、错误、执行时间
  - 超时处理机制：可配置的命令执行超时
  - 重试策略：支持自动重试的配置

- [x] **T1.1.4**: 异常处理标准化 - 已完成 ✅
  - 异常分类：语法错误、运行时错误、超时、无权限
  - 异常信息序列化：便于服务端日志记录
  - 熔断机制：防止异常命令持续执行

### 1.2 模拟无障碍树实现

- [x] **T1.2.1**: 无障碍树生成器核心 (`A11yTreeGenerator`) - 已完成 ✅
  - 元素角色推断引擎：`getRole()` 实现
  - 元素名称提取：`getAccessibleName()` 实现
  - 元素状态检测：`getState()` 实现

- [x] **T1.2.2**: 无障碍节点数据结构设计 - 已完成 ✅
  ```typescript
  interface A11yNode {
    id: string;           // 唯一标识
    role: string;         // 角色 (button, textbox, link...)
    name: string;         // 可访问名称
    description?: string; // 描述
    state: Record<string, boolean>; // 状态 (disabled, checked...)
    tag: string;          // 标签名
    selector: string;     // CSS 选择器
    value?: string;       // 输入值
    children: string[];   // 子节点 IDs
    boundingBox?: { x, y, width, height }; // 边界框
  }
  ```

- [x] **T1.2.3**: 语义标签映射 - 已完成 ✅
  - HTML5 语义标签 → ARIA role 映射 (nav → navigation, main → main...)
  - 隐式角色推断：button、input、a 等原生标签

- [x] **T1.2.4**: 交互式元素过滤 - 已完成 ✅
  - 只包含可交互元素：button、input、select、a、[role]...
  - 过滤不可见元素：`offsetParent === null`
  - 过滤装饰性元素：空 alt 的图片等

- [x] **T1.2.5**: 无障碍树导出接口 - 已完成 ✅
  - `getFullA11yTree()`: 获取完整树
  - `getPartialA11yTree(rootId)`: 获取子树
  - `getFocusedElement()`: 获取焦点元素
  - `queryA11yTree(predicate)`: 条件查询

### 1.3 工具执行器增强

- [x] **T1.3.1**: BaseTool 抽象类重构 ✅
  - 统一执行接口：`execute(params) → Promise<Result>`
  - 执行前校验：`validate(params) → ValidationResult`
  - 执行上下文：`ExecutionContext` (tabId, world)

- [x] **T1.3.2**: 现有工具迁移 ✅
  - `click` → 重构为标准工具格式
  - `fill` → 添加多行输入支持
  - `navigate` → 支持相对路径
  - `inject` → 支持注入模式 (MAIN/ISOLATED)

- [x] **T1.3.3**: 新增基础工具 ✅
  - `scroll`: 滚动到元素/坐标/百分比
  - `screenshot`: 页面/元素截图
  - `wait`: 显式等待条件
  - `keyboard`: 键盘事件

### 1.4 插件端录制回放基础

- [x] **T1.4.1**: 事件监听器实现 (`EventListener`) ✅
  - 鼠标事件：`mousedown`, `mouseup`, `click`, `dblclick`
  - 键盘事件：`keydown`, `keyup`, `keypress`
  - 输入事件：`input`, `change`, `focus`, `blur`
  - 导航事件：`beforeunload`, `hashchange`

- [x] **T1.4.2**: 操作序列数据结构 ✅
  ```typescript
  interface RecordedAction {
    id: string;
    type: 'click' | 'input' | 'scroll' | 'key' | 'navigate';
    timestamp: number;
    target: {
      selector: string;
      a11yRole?: string;
      text?: string;
    };
    params: Record<string, any>;
    pageUrl: string;
    pageTitle: string;
  }
  ```

- [x] **T1.4.3**: 录制控制器 ✅
  - `startRecording()`: 初始化录制状态
  - `stopRecording()`: 停止并返回操作序列
  - `pauseRecording()` / `resumeRecording()`

- [x] **T1.4.4**: 回放引擎基础 ✅
  - 操作序列解析
  - 操作到工具的映射
  - 回放速度控制

---

## Phase 2: Python 服务端 - 核心架构重构

### 2.1 项目结构设计

```
python/
├── core/                          # 核心模块
│   ├── __init__.py
│   ├── exceptions.py              # 异常定义
│   ├── result.py                  # 统一返回结构
│   ├── context.py                 # 执行上下文
│   └── types.py                   # 类型定义
│
├── tools/                         # 工具工厂
│   ├── __init__.py
│   ├── base.py                    # Tool 抽象基类
│   ├── factory.py                 # ToolFactory
│   ├── registry.py                # ToolRegistry
│   ├── browser/                   # 浏览器工具
│   │   ├── click.py
│   │   ├── fill.py
│   │   ├── navigate.py
│   │   ├── scroll.py
│   │   ├── screenshot.py
│   │   ├── inject.py
│   │   ├── evaluate.py
│   │   └── ...
│   └── custom/                    # 自定义工具
│       ├── __init__.py
│       └── ...
│
├── flows/                         # 流程引擎
│   ├── __init__.py
│   ├── engine.py                  # FlowEngine
│   ├── context.py                 # FlowContext
│   ├── steps/                     # 流程步骤
│   │   ├── __init__.py
│   │   ├── base.py                # FlowStep
│   │   ├── action.py              # 动作步骤
│   │   ├── condition.py           # 条件步骤
│   │   ├── loop.py                # 循环步骤
│   │   └── parallel.py            # 并发步骤
│   └── parsers/                   # 流程解析
│       ├── json.py                # JSON 流程解析
│       └── yaml.py                # YAML 流程解析
│
├── api/                           # API 层
│   ├── __init__.py
│   ├── app.py                     # FastAPI 应用
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tools.py               # 工具相关接口
│   │   ├── flows.py               # 流程相关接口
│   │   ├── execute.py             # 执行接口
│   │   ├── record.py              # 录制接口
│   │   └── debug.py               # 调试接口
│   └── schemas/                   # 请求/响应模型
│
├── recorder/                      # 录制回放
│   ├── __init__.py
│   ├── recorder.py                # 录制控制器
│   ├── player.py                  # 回放控制器
│   ├── optimizer.py               # AI 优化器
│   └── storage.py                 # 录制存储
│
├── logger/                        # 日志系统
│   ├── __init__.py
│   ├── config.py                  # 日志配置
│   ├── formatters.py              # 格式化器
│   ├── handlers.py                # 处理器
│   └── analysis.py                # 日志分析
│
├── client/                        # WebSocket 客户端
│   ├── __init__.py
│   ├── connection.py              # 连接管理
│   ├── sender.py                  # 消息发送
│   ├── receiver.py                # 消息接收
│   └── exceptions.py              # 客户端异常
│
├── services/                      # 业务服务
│   ├── __init__.py
│   ├── tool_service.py            # 工具服务
│   ├── flow_service.py            # 流程服务
│   └── execution_service.py       # 执行服务
│
├── models/                        # 数据模型
│   ├── __init__.py
│   ├── tool.py                    # 工具模型
│   ├── flow.py                    # 流程模型
│   ├── action.py                  # 动作模型
│   └── execution.py               # 执行模型
│
└── utils/                         # 工具函数
    ├── __init__.py
    ├── selectors.py               # 选择器工具
    ├── timing.py                  # 时间工具
    └── json_utils.py              # JSON 工具
```

### 2.2 核心抽象层实现

- [x] **T2.2.1**: 统一返回结构 (`Result[T]`) ✅
  ```python
  class Result[T]:
      success: bool
      data: T | None
      error: Error | None
      meta: ResultMeta  # 执行时间、工具名称等

  class Error:
      code: str
      message: str
      details: dict | None
      recoverable: bool
  ```

- [x] **T2.2.2**: 工具抽象基类 (`Tool`) ✅
  ```python
  class Tool(Generic[TParams, TResult]):
      name: str
      description: str
      parameters: ToolParameters  # JSON Schema

      async def execute(
          params: TParams,
          context: ExecutionContext
      ) -> ToolResult[TResult]:
          ...

      async def validate(params: TParams) -> ValidationResult:
          ...
  ```

- [x] **T2.2.3**: 执行上下文 (`ExecutionContext`) ✅
  - Tab 会话管理
  - 变量作用域链
  - 执行状态跟踪
  - 资源清理钩子

- [x] **T2.2.4**: 工具参数 Schema 定义 ✅
  - 基于 Pydantic + JSON Schema
  - 参数验证器工厂
  - 参数文档生成

### 2.3 工具工厂与注册表

- [x] **T2.3.1**: 工具注册表 (`ToolRegistry`) ✅
  - 工具注册/注销
  - 按名称/标签查询
  - 工具发现机制
  - 工具版本管理

- [x] **T2.3.2**: 工具工厂 (`ToolFactory`) ✅
  - 工具实例化
  - 工具初始化/销毁
  - 工具依赖注入

- [x] **T2.3.3**: 内置浏览器工具实现 ✅
  - `browser.click`: 点击元素
  - `browser.fill`: 填充输入框
  - `browser.select`: 选择选项
  - `browser.navigate`: 导航到 URL
  - `browser.scroll`: 滚动页面
  - `browser.screenshot`: 截图
  - `browser.inject`: 注入脚本
  - `browser.evaluate`: 执行 JS
  - `browser.wait`: 等待条件
  - `browser.get_html`: 获取 HTML
  - `browser.extract`: 提取数据
  - `browser.keyboard`: 键盘输入

- [x] **T2.3.4**: 工具描述接口 ✅
  ```python
  GET /api/v1/tools
  # 返回所有可用工具列表
  [
    {
      "name": "browser.click",
      "description": "点击页面上的元素",
      "parameters": {
        "type": "object",
        "properties": {
          "selector": {"type": "string", "description": "CSS 选择器"},
          "button": {"type": "string", "enum": ["left", "middle", "right"]},
          "count": {"type": "integer", "description": "点击次数"}
        },
        "required": ["selector"]
      }
    }
  ]
  ```

- [x] **T2.3.5**: 自定义工具开发规范 ✅
  - 自定义工具注册
  - 工具间依赖
  - 工具钩子机制

### 2.4 流程引擎

- [x] **T2.4.1**: 流程引擎核心 (`FlowEngine`) - 已完成 ✅
  - 流程定义解析
  - 步骤调度
  - 上下文传递
  - 错误恢复

- [x] **T2.4.2**: 流程步骤类型 ✅
  - `ActionStep`: 执行工具调用
  - `ConditionStep`: 条件分支
  - `LoopStep`: 循环执行
  - `ParallelStep`: 并发执行
  - `ParallelBranchStep`: 并发分支
  - `WaitStep`: 等待
  - `SubFlowStep`: 子流程
  - `SetVarStep`: 设置变量
  - `LogStep`: 记录日志

- [x] **T2.4.3**: 流程定义格式 ✅
  ```yaml
  # 流程示例
  id: login_flow
  name: 登录流程
  description: 执行标准登录流程

  variables:
    username: ""
    password: ""
    login_result: null

  steps:
    - name: 打开登录页面
      type: action
      tool: browser.navigate
      params:
        url: "${LOGIN_URL}"

    - name: 输入用户名
      type: action
      tool: browser.fill
      params:
        selector: "#username"
        value: "${username}"

    - name: 输入密码
      type: action
      tool: browser.fill
      params:
        selector: "#password"
        value: "${password}"

    - name: 点击登录按钮
      type: action
      tool: browser.click
      params:
        selector: "#submit"

    - name: 等待登录结果
      type: action
      tool: browser.wait
      params:
        selector: ".logged-in"
        timeout: 10000

    - name: 检查是否登录成功
      type: condition
      condition: "${login_result.success}"
      on_true:
        - name: 登录成功
          type: log
          message: "登录成功"
      on_false:
        - name: 登录失败
          type: log
          message: "登录失败: ${login_result.error}"
  ```

- [x] **T2.4.4**: 流程存储与管理 ✅
  - 流程版本控制
  - 流程导入/导出
  - 流程分类标签

### 2.5 API 层实现

- [x] **T2.5.1**: FastAPI 应用基础 ✅
  - 应用配置
  - 中间件
  - CORS 配置
  - 健康检查

- [x] **T2.5.2**: 工具接口 ✅
  - `GET /api/v1/tools` - 列出所有工具
  - `GET /api/v1/tools/{name}` - 获取工具详情
  - `GET /api/v1/tools/{name}/schema` - 获取工具参数 Schema

- [x] **T2.5.3**: 执行接口 - 已完成 ✅
  - `POST /api/v1/execute` - 执行单个工具调用
  - `POST /api/v1/execute/flow` - 执行流程
  - `GET /api/v1/execute/{execution_id}` - 查询执行状态
  - `DELETE /api/v1/execute/{execution_id}` - 终止执行

- [x] **T2.5.4**: 流程接口 ✅
  - `GET /api/v1/flows` - 列出所有流程
  - `POST /api/v1/flows` - 创建流程
  - `GET /api/v1/flows/{id}` - 获取流程详情
  - `PUT /api/v1/flows/{id}` - 更新流程
  - `DELETE /api/v1/flows/{id}` - 删除流程
  - `POST /api/v1/flows/{id}/run` - 运行流程

- [x] **T2.5.5**: 录制回放接口 ✅
  - `POST /api/v1/record/start` - 开始录制
  - `POST /api/v1/record/stop` - 停止录制
  - `GET /api/v1/record/{id}` - 获取录制结果
  - `POST /api/v1/replay/{id}` - 回放录制
  - `POST /api/v1/record/{id}/optimize` - AI 优化录制

### 2.6 WebSocket 客户端

- [x] **T2.6.1**: 连接管理 (`ConnectionManager`) ✅ (部分)
  - 自动重连
  - 心跳机制
  - 消息队列
  - 注：连接池尚未实现

- [x] **T2.6.2**: 消息协议设计 - 已完成 ✅
  ```json
  // 请求
  {
    "id": "req-uuid",
    "type": "execute",
    "tool": "browser.click",
    "params": {
      "selector": "#submit"
    },
    "timeout": 30000
  }

  // 响应
  {
    "id": "req-uuid",
    "success": true,
    "data": null,
    "error": null,
    "meta": {
      "tool": "browser.click",
      "duration": 125
    }
  }

  // 事件
  {
    "type": "event",
    "event": "navigated",
    "data": {
      "url": "https://..."
    }
  }
  ```

- [x] **T2.6.3**: 同步/异步调用支持 ✅
  - 同步调用：等待结果返回
  - 异步调用：返回执行 ID
  - 流式响应：Server-Sent Events

- [x] **T2.6.4**: 错误处理与重试 ✅
  - 连接错误重试
  - 命令超时处理
  - 部分失败处理

---

## Phase 3: 录制/回放与 AI 优化

### 3.1 录制系统

- [x] **T3.1.1**: 录制状态管理 - 已完成 ✅
  - 录制 ID 生成
  - 录制元数据存储
  - 录制分页/分段

- [x] **T3.1.2**: 操作序列标准化 ✅
  - 录制数据清洗
  - 重复操作合并
  - 等待时间标准化

- [x] **T3.1.3**: 录制数据存储 - 已完成 ✅
  - 本地文件系统存储
  - 录制回放索引
  - 录制版本管理

- [x] **T3.1.4**: 录制回放 WebSocket 接口 ✅
  - 开始/停止录制指令
  - 回放控制指令：播放、暂停、跳转
  - 实时状态同步

### 3.2 回放引擎

- [x] **T3.2.1**: 回放控制器 - 已完成 ✅
  - 操作序列解析
  - 播放速度控制
  - 断点续播

- [x] **T3.2.2**: 选择器适配 - 已完成 ✅
  - 原始选择器优先
  - 备用选择器列表
  - 无障碍树辅助定位
  - 文本内容匹配

- [x] **T3.2.3**: 执行容错 - 已完成 ✅
  - 操作失败重试
  - 页面变化检测
  - 降级策略

- [x] **T3.2.4**: 回放报告生成 ✅
  - 执行结果统计
  - 失败步骤标记
  - 屏幕录制回放

### 3.3 AI 优化器

- [x] **T3.3.1**: 日志分析接口 ✅
  - 执行日志解析
  - 错误模式识别
  - 优化建议生成

- [x] **T3.3.2**: 录制优化流程 ✅
  - 冗余操作识别
  - 参数化处理
  - 错误处理添加

- [x] **T3.3.3**: LLM 集成接口 ✅
  - 日志摘要生成
  - 流程解释生成
  - 修复建议生成

---

## Phase 4: 日志系统

### 4.1 日志架构

- [x] **T4.1.1**: 日志配置 - 已完成 ✅
  - 多级别日志 (DEBUG, INFO, WARNING, ERROR)
  - 多输出目标 (文件、控制台、远程)
  - 日志格式标准化

- [x] **T4.1.2**: 执行日志结构 - 已完成 ✅
  - ExecutionLogEntry 数据类
  - ExecutionLogger 记录器
  - ExecutionLogManager 管理器

- [x] **T4.1.3**: 上下文日志 - 已完成 ✅
  - 变量变化记录 (通过 context 参数)
  - 流程分支记录 (通过 step_name)
  - 异常堆栈跟踪 (通过 error 参数)

### 4.2 日志分析

- [x] **T4.2.1**: 日志查询接口 ✅
  - 按执行 ID 查询
  - 按时间范围查询
  - 按工具类型查询
  - 按错误状态查询

- [x] **T4.2.2**: 日志统计 ✅
  - 执行成功率统计
  - 平均执行时间
  - 失败原因分类

- [x] **T4.2.3**: 日志导出 ✅
  - JSON 导出
  - HTML 报告生成
  - CSV 格式导出

---

## Phase 5: 工具与流程库

### 5.1 网站特定工具

- [ ] **T5.1.1**: 工具目录结构
  ```
  tools/
  ├── __init__.py
  ├── browser/          # 浏览器基础工具
  ├── xiaohongshu/      # 小红书工具
  │   ├── __init__.py
  │   ├── publish.py    # 发布笔记
  │   ├── comment.py    # 评论区操作
  │   └── search.py     # 搜索功能
  ├── douyin/           # 抖音工具
  │   └── ...
  └── platform/         # 通用平台工具
      └── ...
  ```

- [ ] **T5.1.2**: 工具描述注册
  - 自动扫描工具注册
  - 工具分类标签
  - 工具依赖声明

### 5.2 流程模板库

- [ ] **T5.2.1**: 流程目录结构
  ```
  flows/
  ├── browser/           # 浏览器操作流程
  ├── xiaohongshu/       # 小红书流程
  │   ├── publish-note.yaml
  │   ├── like-note.yaml
  │   └── follow-user.yaml
  └── templates/         # 通用模板
      ├── login.yaml
      ├── scrape.yaml
      └── automation.yaml
  ```

- [ ] **T5.2.2**: 流程复用机制
  - 流程引用 (import)
  - 流程参数化
  - 流程继承

---

## Phase 6: 测试与文档

### 6.1 测试体系

- [ ] **T6.1.1**: 单元测试
  - 核心模块测试
  - 工具测试
  - API 测试

- [ ] **T6.1.2**: 集成测试
  - 插件-服务端通信测试
  - 流程执行测试
  - 录制回放测试

- [ ] **T6.1.3**: 端到端测试
  - 真实浏览器测试
  - 性能测试

### 6.2 文档

- [ ] **T6.2.1**: API 文档
  - OpenAPI 规范
  - 接口使用示例
  - 错误码说明

- [ ] **T6.2.2**: 开发文档
  - 工具开发指南
  - 流程编写指南
  - 架构设计说明

- [ ] **T6.2.3**: 用户文档
  - 快速开始
  - 工具列表
  - 示例流程

---

## 优先级排序

| 优先级 | 任务 | 预计工作量 |
|--------|------|------------|
| P0 | T1.2.1 模拟无障碍树核心 | 中 |
| P0 | T2.2.1 统一返回结构 | 低 |
| P0 | T2.2.2 工具抽象基类 | 中 |
| P0 | T2.3.3 浏览器工具实现 | 高 |
| P0 | T2.6.2 WebSocket 消息协议 | 中 |
| P1 | T1.1.1 CDP 兼容层 | 高 |
| P1 | T1.1.3 命令执行反馈 | 中 |
| P1 | T1.1.4 异常处理 | 中 |
| P1 | T2.2.3 执行上下文 | 中 |
| P1 | T2.3.1 工具注册表 | 中 |
| P1 | T2.5.3 执行接口 | 中 |
| P1 | T2.6.1 连接管理 | 中 |
| P2 | T1.2.4 交互式元素过滤 | 中 |
| P2 | T1.3.1 BaseTool 重构 | 中 |
| P2 | T2.4.1 流程引擎核心 | 高 |
| P2 | T3.1 录制系统 | 高 |
| P3 | T2.4.3 流程定义格式 | 中 |
| P3 | T3.2 回放引擎 | 高 |
| P3 | T3.3 AI 优化器 | 中 |
| P3 | T4 日志系统 | 中 |

---

## 里程碑

### Milestone 1: 基础通信与工具执行 ✅
- [x] WebSocket 客户端基础功能
- [x] 基础浏览器工具 (click, fill, navigate)
- [x] 统一返回结构

### Milestone 2: 模拟无障碍树 ✅
- [x] 无障碍树生成器
- [x] 无障碍树查询接口
- [x] 集成到工具执行中

### Milestone 3: 工具系统完善 ✅
- [x] 工具工厂与注册表
- [x] API 接口 (tools, execute)
- [x] 所有内置工具实现

### Milestone 4: 流程引擎 ✅
- [x] 流程定义格式
- [x] 流程引擎核心
- [x] 流程 API

### Milestone 5: 录制回放 ✅
- [x] 事件监听器
- [x] 录制/回放接口
- [x] 选择器适配

### Milestone 6: 日志与优化 ✅
- [x] 日志系统
- [x] AI 优化器接口
- [x] 工具/流程库

---

> 最后更新: 2026-02-13
> 负责模块: 全项目重构
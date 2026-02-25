# 多插件密钥通信 - 任务清单

## 需求概述

为插件->服务端->后端的通信增加密钥认证机制，实现：
1. 插件端：根据机器信息生成唯一密钥
2. 服务端：支持多个插件连接，按密钥路由
3. 控制端：连接时传入密钥来指定目标插件
4. 后端：操作浏览器时传入密钥参数

## 架构设计

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   插件A      │     │   插件B      │     │   插件C      │
│  key: key_A  │     │  key: key_B  │     │  key: key_C  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────┐
│                   Relay Server                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ key_A   │  │ key_B   │  │ key_C   │  ...  │
│  │ ws_A    │  │ ws_B    │  │ ws_C    │       │
│  └─────────┘  └─────────┘  └─────────┘       │
└──────────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                 后端控制端 (SilentAgentClient)   │
│  - 传入 key 参数选择目标插件                    │
│  - 通过 key 路由到对应的插件                    │
└─────────────────────────────────────────────────────┘
```

## 任务清单

### Phase 1: 插件端 - 密钥生成与传输

- [x] 1.1 修改 extension/background.js - NeuroneWSClient
  - 新增 `secretKey` 属性存储密钥
  - 修改 `connect(url)` 方法支持传入密钥参数
  - 在 HELLO 消息中携带密钥信息

- [x] 1.2 实现插件端密钥生成逻辑
  - 根据机器信息（navigator.userAgent, chrome.runtime.id 等）生成唯一密钥
  - 支持手动设置固定密钥（用于测试）
  - 将密钥存储到 chrome.storage.local

- [x] 1.3 密钥验证逻辑
  - 服务端 HELLO 响应需要携带密钥
  - 插件端验证密钥匹配后才建立连接

### Phase 2: 服务端 - 多插件路由支持

- [x] 2.1 修改 relay_server.py - RelayState 数据结构
  - 从单一 `extension_ws` 改为字典 `extensions: Dict[str, WebSocket]`
  - key -> {ws, extension_id, version, tools}

- [x] 2.2 修改 /extension 路径处理
  - 接收密钥参数（在 URL query 或 HELLO 消息中）
  - 按密钥存储和管理多个扩展连接
  - 处理密钥冲突（已存在的 key 返回错误）

- [x] 2.3 修改工具调用逻辑
  - execute_tool 方法增加 key 参数
  - 根据 key 路由到对应的插件
  - 支持广播到所有已连接的插件

- [x] 2.4 扩展事件广播
  - extension_connected 事件携带 key 信息
  - 支持按 key 查询扩展状态

### Phase 3: 控制端 - 密钥参数支持

- [x] 3.1 修改 ConnectionConfig
  - 新增 `secret_key` 参数
  - 在 URL 或首条消息中携带密钥

- [x] 3.2 修改 ConnectionManager
  - 连接时传递密钥到服务端
  - 根据密钥维护对应的扩展连接状态

- [x] 3.3 修改 SilentAgentClient (src/client/client.py)
  - 构造函数增加 `secret_key` 参数
  - 所有浏览器工具调用携带密钥参数

- [x] 3.4 修改 relay_client.py (如果使用)
  - 同步增加密钥参数支持

### Phase 4: 后端 API 层 - 密钥参数透传

- [x] 4.1 修改 API execute 路由
  - 接收并透传 secret_key 参数
  - 将密钥传递给 execute_tool 调用

- [x] 4.2 修改浏览器工具基类
  - ExecutionContext 增加 secret_key 字段
  - control.py 调用时传递密钥

- [x] 4.3 业务工具透传（统一抽象）
  - _execute_business_tool 统一获取 secret_key
  - 业务工具通过 context.secret_key 访问
  - 无需每个业务工具单独实现获取逻辑

### Phase 5: 安全性增强（可选）

- [ ] 5.1 密钥加密传输（HTTPS/WSS）
- [ ] 5.2 密钥动态刷新机制
- [ ] 5.3 连接鉴权验证

### Phase 6: 测试与文档

- [ ] 6.1 单元测试覆盖
- [ ] 6.2 多插件同时连接测试
- [ ] 6.3 更新 README 文档

## 关键文件修改清单

| 文件 | 修改内容 |
|------|----------|
| extension/background.js | NeuroneWSClient 增加密钥支持 |
| src/relay_server.py | RelayState 改为字典，支持多插件路由 |
| src/client/connection.py | ConnectionConfig 增加 secret_key |
| src/client/client.py | SilentAgentClient 传递密钥参数 |
| src/api/routes/execute.py | API 层透传密钥 |
| src/tools/base.py | 工具基类增加密钥字段 |

## 消息协议变更

### 插件 -> 服务端 HELLO
```json
{
  "type": "hello",
  "extensionId": "xxx",
  "version": "1.0.0",
  "tools": [...],
  "secretKey": "generated_key"  // 新增
}
```

### 控制端 -> 服务端 executeTool
```json
{
  "id": 1,
  "method": "executeTool",
  "params": {
    "name": "chrome_navigate",
    "args": {...},
    "secretKey": "target_key"  // 新增：指定目标插件
  }
}
```

### 服务端 -> 插件 tool_call（携带密钥）
```json
{
  "type": "tool_call",
  "requestId": "xxx",
  "secretKey": "target_key",  // 新增
  "payload": {...}
}
```
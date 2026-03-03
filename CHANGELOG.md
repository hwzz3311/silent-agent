# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **浏览器客户端模块** (`src/browser/`)
  - `BrowserClient`: 抽象基类定义统一接口
  - `BrowserMode`: 枚举支持 extension/puppeteer/hybrid 三种模式
  - `BrowserClientFactory`: 工厂类根据配置创建对应客户端
  - `ExtensionClient`: 封装现有 relay_client
  - `PuppeteerClient`: Puppeteer 控制，支持 stealth
  - `HybridClient`: 混合模式，结合两者优势
- **端口层** (`src/ports/`)
  - `BrowserPort`: 浏览器操作抽象接口（依赖倒置）
  - `BrowserPortAdapter`: BrowserClient 适配器
- **核心异常** (`src/core/exception.py`)
  - `ToolException`: 工具异常基类
  - `LoginRequiredException`: 需要登录异常
  - `ElementNotFoundException`: 元素未找到异常
  - `SelectorInvalidException`: 选择器无效异常
  - `BrowserConnectionException`: 浏览器连接异常
  - `ToolNotFoundException`: 工具未找到异常
  - `ExecutionTimeoutException`: 执行超时异常
  - `ValidationException`: 参数验证异常
  - `NavigationException`: 导航异常
  - `AuthenticationException`: 认证异常
- **配置模块** (`src/config.py`)
  - BrowserSettings/ServerSettings/LogSettings
  - 环境变量配置支持
  - `RunnerConfig`: 运行时配置（支持依赖注入）
- **扩展 CDP 适配器增强**
  - getDebugPort() 获取调试端口
  - getAccessibilityTreeViaCDP() 真实无障碍树

### Changed
- `ExecutionContext` 新增 browser_mode 字段
- `A11yTreeTool` 支持三种模式获取真实无障碍树
- 新增 use_real_tree 参数强制使用真实树
- API 层支持依赖注入获取浏览器客户端
- `ErrorResponse` 新增 `recoverable` 字段

---

## [2.0.1] - 2025-02-27

### Added
- 无障碍树（A11yTree）工具支持

### Fixed
- A11yTreeTool 参数处理并添加自动重连逻辑
- site_tab_map 按密钥初始化逻辑
- 小红书笔记列表获取 - note_id 和 url 提取
- 优化 site_tab_map 初始化逻辑，支持按密钥初始化
- all_urls 授权时的网站撤销/授权逻辑

---

## [2.0.0] - 2025-02-XX

### Added
- 完整的浏览器自动化工具集
- 多插件密钥系统
- WebSocket Relay 服务器
- FastAPI REST 接口

### Changed
- 从 v1 迁移到 v2 架构
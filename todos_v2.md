# Neurone 小红书 RPA 功能实现任务清单

> 创建日期: 2026-02-13
> 更新日期: 2026-02-13 (完整覆盖14个核心工具)

## 项目背景

参考 `xiaohongshu-mcp-extension` 实现小红书专用 RPA 功能，集成到 Neurone Python 后端服务中。

---

## 核心 RPA 工具清单（共 14 个）

| # | 工具名 | 功能 | 状态 | Neurone 对应 |
|---|--------|------|------|-------------|
| 1 | `xhs_inject_script` | 页面注入执行任意 JS | ⏳ 待实现 | `browser.inject` (需适配 xhs 特有参数) |
| 2 | `xhs_read_page_data` | 读取页面 window/document 数据 | ⏳ 待实现 | `browser.evaluate` (需适配) |
| 3 | `chrome_navigate` | 导航到指定 URL | ✅ 已有 | 直接复用 |
| 4 | `browser_control` | 标签页增删改查 | ✅ 已有 | 直接复用 |
| 5 | `chrome_extract_data` | 从 DOM 元素提取数据 | ✅ 已有 | 直接复用 |
| 6 | `chrome_click` | 点击页面元素 | ✅ 已有 | 直接复用 |
| 7 | `chrome_fill` | 填充表单输入 | ✅ 已有 | 直接复用 |
| 8 | `chrome_keyboard` | 模拟键盘输入 | ✅ 已有 | 直接复用 |
| 9 | `chrome_upload_file` | 上传单个文件 | 🔲 待新增 | 新建工具 |
| 10 | `chrome_set_files` | 设置多个文件到 input | 🔲 待新增 | 新建工具 |
| 11 | `chrome_wait_elements` | 等待元素出现 | ✅ 已有 | 直接复用 |
| 12 | `chrome_set_video_to_page` | 视频分块传输到页面 | 🔲 待新增 (T2) | 新建工具 |
| 13 | `chrome_intercept_upload` | 拦截视频上传请求 | 🔲 待新增 (T3) | 新建工具 |
| 14 | `chrome_download_video_from_url` | 从 URL 下载视频并暂存 | 🔲 待新增 (T1) | 新建工具 |

**状态说明**：
- ✅ 已有：Neurone 已具备，直接复用
- 🔲 待新增：需要新建工具实现
- ⏳ 待实现：需要适配 Neurone 已有工具

---

## 工具详细任务

### Part A: 已有工具复用（无需新建）

#### A.1: 直接复用工具（chrome_navigate, browser_control, chrome_extract_data, chrome_click, chrome_fill, chrome_keyboard, chrome_wait_elements）
- [ ] **A.1.1** 验证现有工具参数与小红书 MCP 工具参数兼容性
- [ ] **A.1.2** 编写小红书场景使用示例
- [ ] **A.1.3** 添加小红书特定选择器配置（如小红书特定元素选择器）

---

### Part B: 适配已有工具（需适配参数/返回值）

#### B.1: 注入脚本适配 (xhs_inject_script → browser.inject)

- [ ] **B.1.1** 分析 `xhs_inject_script` 特有参数
  - [ ] `code`: 注入代码（必需）
  - [ ] `world`: 执行世界（ISOLATED/MAIN，默认 ISOLATED）
  - [ ] `args`: 传递给代码的参数
  - [ ] `tabId`: 指定标签页

- [ ] **B.1.2** 创建适配层 `xhs_inject_script.py`
  - [ ] 封装 `browser.inject` 支持 `world` 参数
  - [ ] 支持 MAIN/ISOLATED 双世界注入
  - [ ] 处理 ISOLATED → MAIN 跨世界通信（类似小红书的 inject-bridge.js）

- [ ] **B.1.3** 跨世界通信桥接实现
  - [ ] 实现 `main_world_executor.js` 注入逻辑
  - [ ] 实现 CustomEvent 消息传递机制
  - [ ] 处理超时和错误

- [ ] **B.1.4** 测试用例
  - [ ] 测试 ISOLATED 世界注入
  - [ ] 测试 MAIN 世界注入
  - [ ] 测试跨世界参数传递
  - [ ] 测试超时处理

---

#### B.2: 页面数据读取适配 (xhs_read_page_data → browser.evaluate)

- [ ] **B.2.1** 分析 `xhs_read_page_data` 参数
  - [ ] `path`: 属性路径（如 `location.href`, `__INITIAL_STATE__`）

- [ ] **B.2.2** 创建适配层 `xhs_read_page_data.py`
  - [ ] 支持 dotted path 解析（如 `__INITIAL_STATE__.user.id`）
  - [ ] 处理循环引用和函数
  - [ ] 返回结构化数据 + 类型信息

- [ ] **B.2.3** 测试用例
  - [ ] 测试简单 path（如 `location.href`）
  - [ ] 测试嵌套 path（如 `__INITIAL_STATE__`）
  - [ ] 测试循环引用处理

---

### Part C: 新建工具（尚未实现）

#### T1: 视频下载工具 (chrome_download_video_from_url)

- [ ] **T1.1** 创建 `video_download.py` 工具文件
  - [ ] 实现 `VideoDownloadTool` 类，继承 `Tool` 抽象基类
  - [ ] 支持 `url` 参数：视频下载地址
  - [ ] 支持 `timeout` 参数：下载超时时间（默认30分钟）
  - [ ] 支持 `tabId` 参数：可选，页面显示进度

- [ ] **T1.2** 视频下载核心逻辑
  - [ ] 实现 HTTP 下载流式读取
  - [ ] 文件类型自动检测（mp4/mov/avi/webm/mkv）
  - [ ] 文件大小验证（最大20GB）

- [ ] **T1.3** 进度回调与页面通知
  - [ ] 实现 `show_progress()` 注入脚本（进度百分比、速度）
  - [ ] 每500ms更新一次页面进度提示

- [ ] **T1.4** 视频暂存管理
  - [ ] 实现 `VideoStore` 类管理暂存视频
  - [ ] 支持 videoId 参数标识
  - [ ] 支持自动清理（30分钟过期）
  - [ ] 存储元数据：文件名、文件类型、文件大小、创建时间

- [ ] **T1.5** 测试用例
  - [ ] 测试普通视频下载
  - [ ] 测试大文件下载
  - [ ] 测试进度回调
  - [ ] 测试超时处理

---

#### T2: 视频分块传输工具 (chrome_set_video_to_page)

- [ ] **T2.1** 创建 `video_chunk_transfer.py` 工具文件
  - [ ] 实现 `VideoChunkTransferTool` 类
  - [ ] 支持 `selector` 参数：文件输入框选择器
  - [ ] 支持 `tabId` 参数：可选
  - [ ] 支持 `clearAfterSet` 参数：设置后是否清除暂存

- [ ] **T2.2** 分块传输核心逻辑
  - [ ] 块大小定义：20MB (20971520 bytes)
  - [ ] 将暂存视频按块分割
  - [ ] 通过 CustomEvent 分块传输到页面 MAIN 世界

- [ ] **T2.3** 页面端接收器实现
  - [ ] 实现 `INIT_VIDEO_RECEIVER` 消息处理
  - [ ] 实现 `VIDEO_CHUNK` 消息处理（接收并组装）
  - [ ] 实现 `SET_VIDEO_TO_INPUT` 消息处理（DataTransfer设置input）

- [ ] **T2.4** 进度回调
  - [ ] 实时更新页面进度提示
  - [ ] 显示当前块/总块数

- [ ] **T2.5** 测试用例
  - [ ] 测试普通视频传输
  - [ ] 测试大视频分块传输
  - [ ] 测试进度回调

---

#### T3: 视频上传拦截工具 (chrome_intercept_upload)

- [ ] **T3.1** 创建 `video_upload_intercept.py` 工具文件
  - [ ] 实现 `VideoUploadInterceptTool` 类
  - [ ] 支持 `tabId` 参数
  - [ ] 支持 `timeout` 参数：默认60秒
  - [ ] 支持 `clearAfterUpload` 参数：上传后清除暂存

- [ ] **T3.2** XHR 拦截器注入
  - [ ] 重写 `XMLHttpRequest.prototype.open`
  - [ ] 标记 upload 请求
  - [ ] 提取 `uploadUrl`（OSS地址）

- [ ] **T3.3** Fetch 拦截器注入
  - [ ] 重写 `window.fetch`
  - [ ] 拦截 upload/video/media 请求
  - [ ] 提取响应中的 `uploadUrl`

- [ ] **T3.4** 上传触发
  - [ ] 查找小红书上传触发元素
  - [ ] 自动点击触发上传
  - [ ] 等待上传完成并返回 uploadUrl

- [ ] **T3.5** 测试用例
  - [ ] 测试 XHR 拦截
  - [ ] 测试 Fetch 拦截
  - [ ] 测试完整上传流程

---

#### T4: 单文件上传工具 (chrome_upload_file)

- [ ] **T4.1** 创建 `upload_file.py` 工具文件
  - [ ] 实现 `UploadFileTool` 类
  - [ ] 支持 `selector` 参数：文件输入框选择器
  - [ ] 支持 `base64Data` 参数：Base64 编码的文件内容
  - [ ] 支持 `fileName` 参数：文件名
  - [ ] 支持 `mimeType` 参数：MIME 类型
  - [ ] 支持 `timeout` 参数

- [ ] **T4.2** 单文件上传核心逻辑
  - [ ] Base64 解码
  - [ ] Uint8Array 转换
  - [ ] File 对象创建
  - [ ] DataTransfer 设置到 input
  - [ ] 触发 change/input 事件

- [ ] **T4.3** 测试用例
  - [ ] 测试图片上传（jpeg/png）
  - [ ] 测试视频上传（mp4）
  - [ ] 测试大文件处理

---

#### T5: 多文件设置工具 (chrome_set_files)

- [ ] **T5.1** 创建 `set_files.py` 工具文件
  - [ ] 实现 `SetFilesTool` 类
  - [ ] 支持 `selector` 参数：文件输入框选择器
  - [ ] 支持 `files` 参数：文件数组（每个含 base64Data, fileName, mimeType）
  - [ ] 支持 `timeout` 参数

- [ ] **T5.2** 多文件设置核心逻辑
  - [ ] 批量 Base64 解码
  - [ ] 多个 File 对象创建
  - [ ] DataTransfer 批量添加
  - [ ] 触发 change/input 事件

- [ ] **T5.3** 测试用例
  - [ ] 测试多图片上传
  - [ ] 测试批量文件设置
  - [ ] 测试空文件数组处理

---

### Part D: 工具注册与集成

- [ ] **D.1** 工具注册
  - [ ] 在 `python/tools/registry.py` 中注册新工具
  - [ ] 注册适配工具（B.1, B.2）
  - [ ] 注册新建工具（T1-T5）

- [ ] **D.2** API 路由配置
  - [ ] 确保工具可通过 REST API 调用
  - [ ] 测试工具列表接口返回新工具

- [ ] **D.3** 文档更新
  - [ ] 更新 README.md 添加新工具说明
  - [ ] 更新工具清单文档

---

### Part E: 流程编排工具

#### T6: 小红书发布流程编排器 (xiaohongshu_publisher)

- [ ] **T6.1** 创建 `xiaohongshu_publisher.py` 流程工具
  - [ ] 实现 `XiaohongshuPublisher` 类

- [ ] **T6.2** 完整发布流程
  - [ ] `publish_note()`: 发布图文笔记流程
    - [ ] 导航到小红书创作中心
    - [ ] 点击发布按钮
    - [ ] 上传图片（使用 T4/T5）
    - [ ] 填写标题和正文
    - [ ] 选择话题和标签
    - [ ] 点击发布

  - [ ] `publish_video()`: 发布视频流程
    - [ ] 下载视频（使用 T1）
    - [ ] 分块传输到页面（使用 T2）
    - [ ] 触发上传拦截获取OSS地址（使用 T3）
    - [ ] 填写标题和正文
    - [ ] 提交发布

- [ ] **T6.3** 辅助方法
  - [ ] `get_upload_input_selector()`: 获取上传输入框选择器
  - [ ] `get_publish_button_selector()`: 获取发布按钮选择器
  - [ ] `get_title_input_selector()`: 获取标题输入框选择器
  - [ ] `get_content_input_selector()`: 获取正文输入框选择器

- [ ] **T6.4** 测试用例
  - [ ] 测试完整发布流程（模拟环境）
  - [ ] 测试各步骤独立运行

---

### Part F: 依赖与配置

- [ ] **F.1** 依赖更新
  - [ ] 检查 `pyproject.toml` 是否需要更新

- [ ] **F.2** 配置项
  - [ ] 添加视频暂存目录配置（默认 `~/.neurone/videos`）
  - [ ] 添加最大文件大小配置（默认 20GB）
  - [ ] 添加分块大小配置（默认 20MB）

---

## 技术参考

### 小红书 MCP 原生工具 → Neurone 实现映射

| 原生工具 | Neurone 实现 | 实现方式 |
|----------|-------------|----------|
| `xhs_inject_script` | `XHSInjectScriptTool` | 新建适配层 (Part B.1) |
| `xhs_read_page_data` | `XHSReadPageDataTool` | 新建适配层 (Part B.2) |
| `chrome_download_video_from_url` | `VideoDownloadTool` | 新建 (T1) |
| `chrome_set_video_to_page` | `VideoChunkTransferTool` | 新建 (T2) |
| `chrome_intercept_upload` | `VideoUploadInterceptTool` | 新建 (T3) |
| `chrome_upload_file` | `UploadFileTool` | 新建 (T4) |
| `chrome_set_files` | `SetFilesTool` | 新建 (T5) |

### Neurone 现有架构复用

- `Tool` 抽象基类 (`python/tools/base.py`)
- `ToolRegistry` (`python/tools/registry.py`)
- `ExecutionContext` (`python/core/context.py`)
- `Result[T]` (`python/core/result.py`)

---

## 执行顺序建议

```
Phase 1: 适配层 (B)
├── B.1: xhs_inject_script 适配
└── B.2: xhs_read_page_data 适配

Phase 2: 新建工具 (T)
├── T1: 视频下载工具
├── T2: 视频分块传输工具
├── T3: 视频上传拦截工具
├── T4: 单文件上传工具
└── T5: 多文件设置工具

Phase 3: 集成与注册 (D)
├── 注册所有新工具
└── API 路由配置

Phase 4: 流程编排 (T6)
└── 小红书发布流程编排器

Phase 5: 收尾 (F)
├── 配置更新
└── 文档完善
```

---

## 验收标准

- [ ] 14 个核心工具全部覆盖
- [ ] 适配工具继承 `Tool` 基类
- [ ] 新建工具继承 `Tool` 基类
- [ ] 所有工具返回 `Result[T]` 统一格式
- [ ] 工具可通过 `/api/v1/execute` 调用
- [ ] 新工具出现在 `/api/v1/tools` 列表中
- [ ] 有完整的单元测试覆盖
- [ ] 文档更新完成
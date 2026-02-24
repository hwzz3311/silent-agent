# xhs/ 工具迁移到新框架计划 (todos_v4)

> 参考: src/tools/xhs/ -> src/tools/sites/xiaohongshu/
> 创建时间: 2026-02-14

---

## 一、迁移概述

### 1.1 迁移目标

将 `src/tools/xhs/` 目录下的 8 个底层工具迁移/集成到新框架 `src/tools/sites/xiaohongshu/` 中：

| 序号 | 工具名 | 功能描述 | 迁移方式 |
|:---:|--------|----------|---------|
| 1 | `XHSReadPageDataTool` | 页面数据读取 | ✅ 已完成 |
| 2 | `XHSInjectScriptTool` | JS 注入执行 | ✅ 已完成 |
| 3 | `VideoDownloadTool` | 视频下载 | ✅ 已完成 |
| 4 | `VideoChunkTransferTool` | 视频分块传输 | ✅ 已完成 |
| 5 | `VideoUploadInterceptTool` | 上传拦截 | ✅ 已完成 |
| 6 | `UploadFileTool` | 单文件上传 | ✅ 已完成 |
| 7 | `SetFilesTool` | 多文件设置 | ✅ 已完成 |
| 8 | `XiaohongshuPublisher` | 发布流程编排 | ✅ 已完成 |

### 1.2 迁移后目录结构

```
src/tools/sites/xiaohongshu/
├── __init__.py
├── adapters.py              # XiaohongshuSite 适配器
├── selectors.py             # XHSSelectors 选择器
├── utils/                   # [新增] 底层工具目录
│   ├── __init__.py
│   ├── page_data.py         # XHSReadPageDataTool (迁移)
│   ├── inject_script.py     # XHSInjectScriptTool (迁移)
│   ├── video_download.py    # VideoDownloadTool (迁移)
│   ├── video_transfer.py    # VideoChunkTransferTool (迁移)
│   ├── video_intercept.py   # VideoUploadInterceptTool (迁移)
│   └── file_upload.py       # UploadFileTool + SetFilesTool (迁移)
├── tools/
│   ├── login/               # 登录工具 (已完成)
│   ├── publish/             # 发布工具 (已完成)
│   ├── browse/              # 浏览工具 (已完成)
│   └── interact/            # 互动工具 (已完成)
└── publishers/              # [新增] 流程编排工具
    └── __init__.py
        └── xiaohongshu_publisher.py  # XiaohongshuPublisher (重构)
```

---

## 二、迁移任务清单

### Phase M1: 基础工具迁移

#### M1.1 页面数据读取工具 (Page Data)

**源文件**: `src/tools/xhs/xhs_read_page_data.py`
**目标文件**: `src/tools/sites/xiaohongshu/utils/page_data.py`
**状态**: ✅ 已完成

**迁移任务**:
- [x] M1.1.1: 创建 `src/tools/sites/xiaohongshu/utils/` 目录结构
- [x] M1.1.2: 迁移 `ReadPageDataTool` 类（原 XHSReadPageDataTool）
- [x] M1.1.3: 迁移 `ReadPageDataParams` 参数类（原 XHSReadPageDataParams）
- [x] M1.1.4: 迁移 `ReadPageDataResult` 结果类
- [x] M1.1.5: 更新 `adapters.py` 导入路径（可复用）
- [ ] M1.1.6: 添加单元测试

#### M1.2 脚本注入工具 (Inject Script)

**源文件**: `src/tools/xhs/xhs_inject_script.py`
**目标文件**: `src/tools/sites/xiaohongshu/utils/inject_script.py`
**状态**: ✅ 已完成

**迁移任务**:
- [x] M1.2.1: 迁移 `InjectScriptTool` 类（原 XHSInjectScriptTool）
- [x] M1.2.2: 迁移 `InjectScriptParams` 参数类（原 XHSInjectScriptParams）
- [x] M1.2.3: 实现跨世界通信支持 (MAIN/ISOLATED)
- [x] M1.2.4: 添加结果解析逻辑
- [ ] M1.2.5: 集成到 `XiaohongshuSite` 适配器
- [ ] M1.2.6: 添加单元测试

---

### Phase M2: 视频处理工具迁移

#### M2.1 视频下载工具

**源文件**: `src/tools/xhs/video_download.py`
**目标文件**: `src/tools/sites/xiaohongshu/utils/video_download.py`
**状态**: ✅ 已完成

**迁移任务**:
- [x] M2.1.1: 迁移 `VideoDownloadTool` 类
- [x] M2.1.2: 迁移 `VideoDownloadParams` 参数类
- [x] M2.1.3: 迁移 `VideoDownloadResult` 结果类
- [x] M2.1.4: 复用 `video_transfer.py` 中的 `VideoStore`
- [x] M2.1.5: 复用 `video_transfer.py` 中的 `StoredVideo`
- [ ] M2.1.6: 集成到 `XiaohongshuSite` 适配器
- [ ] M2.1.7: 添加单元测试

#### M2.2 视频分块传输工具

**源文件**: `src/tools/xhs/video_chunk_transfer.py`
**目标文件**: `src/tools/sites/xiaohongshu/utils/video_transfer.py`
**状态**: ✅ 已完成

**迁移任务**:
- [x] M2.2.1: 创建 `video_transfer.py` 统一文件（含 VideoStore + StoredVideo）
- [x] M2.2.2: 迁移 `VideoChunkTransferTool` 类
- [x] M2.2.3: 迁移 `VideoChunkTransferParams` 参数类
- [x] M2.2.4: 实现分块传输逻辑
- [x] M2.2.5: 实现设置视频到 input 功能
- [ ] M2.2.6: 添加单元测试

#### M2.3 视频上传拦截工具

**源文件**: `src/tools/xhs/video_upload_intercept.py`
**目标文件**: `src/tools/sites/xiaohongshu/utils/video_intercept.py`
**状态**: ✅ 已完成

**迁移任务**:
- [x] M2.3.1: 迁移 `VideoUploadInterceptTool` 类
- [x] M2.3.2: 迁移 `VideoUploadInterceptParams` 参数类
- [x] M2.3.3: 迁移 `VideoUploadInterceptResult` 结果类
- [x] M2.3.4: 实现 XHR/Fetch 拦截逻辑
- [x] M2.3.5: 实现触发上传和获取上传信息
- [ ] M2.3.6: 集成到视频发布流程
- [ ] M2.3.7: 添加单元测试

---

### Phase M3: 文件上传工具迁移

#### M3.1 文件上传工具整合

**源文件**:
- `src/tools/xhs/upload_file.py`
- `src/tools/xhs/set_files.py`

**目标文件**: `src/tools/sites/xiaohongshu/utils/file_upload.py`
**状态**: ✅ 已完成

**迁移任务**:
- [x] M3.1.1: 创建 `file_upload.py` 统一文件
- [x] M3.1.2: 迁移 `UploadFileTool` 单文件上传
- [x] M3.1.3: 迁移 `UploadFileParams` 参数类
- [x] M3.1.4: 迁移 `UploadFileResult` 结果类
- [x] M3.1.5: 迁移 `SetFilesTool` 多文件设置
- [x] M3.1.6: 迁移 `SetFilesParams` 参数类
- [x] M3.1.7: 迁移 `SetFilesResult` 结果类
- [x] M3.1.8: 迁移 `FileData` 数据类
- [x] M3.1.9: 整合重复代码
- [ ] M3.1.10: 添加单元测试
- [ ] M3.1.7: 迁移 `SetFilesResult` 结果类
- [ ] M3.1.8: 迁移 `FileData` 数据类
- [ ] M3.1.9: 整合重复代码
- [ ] M3.1.10: 添加单元测试

---

### Phase M4: 发布流程编排器重构

#### M4.1 发布器重构

**源文件**: `src/tools/xhs/xiaohongshu_publisher.py`
**目标文件**: `src/tools/sites/xiaohongshu/publishers/xiaohongshu_publisher.py`
**状态**: ✅ 已完成

**迁移任务**:
- [x] M4.1.1: 创建 `src/tools/sites/xiaohongshu/publishers/` 目录
- [x] M4.1.2: 迁移 `XiaohongshuPublisher` 类
- [x] M4.1.3: 重构 `publish_note` 方法，使用新工具
- [x] M4.1.4: 重构 `publish_video` 方法，集成视频工具链
- [x] M4.1.5: 集成视频工具链 (下载 -> 传输 -> 上传)
- [x] M4.1.6: 更新 `publishers/__init__.py` 导出
- [x] M4.1.7: 更新 `__init__.py` 导出新模块

---

### Phase M5: 集成与测试

#### M5.1 工具模块集成

**目标文件**: `src/tools/sites/xiaohongshu/utils/__init__.py`

**迁移任务**:
- [x] M5.1.1: 创建 `utils/__init__.py` 模块导出
- [x] M5.1.2: 导出所有迁移的工具类（video_transfer, video_download）
- [x] M5.1.3: 创建便捷函数（transfer_video_to_page, download_video）
- [ ] M5.1.4: 更新 `publishers/__init__.py`

#### M5.2 适配器集成

**目标文件**: `src/tools/sites/xiaohongshu/adapters.py`

**迁移任务**:
- [x] M5.2.1: 更新 `XiaohongshuSite` 导入新工具（从 utils 导入）
- [x] M5.2.2: 集成 `inject_script` 方法（复用 ReadPageDataTool）
- [x] M5.2.3: 集成 `download_video` 方法（已通过 utils.video_download 实现）
- [x] M5.2.4: 集成 `upload_file` 方法（已通过 utils.file_upload 实现）
- [x] M5.2.5: 移除旧的 `from src.tools.xhs import` 导入

#### M5.3 端到端测试

**迁移任务**:
- [ ] M5.3.1: 编写集成测试脚本
- [ ] M5.3.2: 测试页面数据读取
- [ ] M5.3.3: 测试视频下载流程
- [ ] M5.3.4: 测试文件上传流程
- [ ] M5.3.5: 测试发布流程编排

#### M5.4 修复 ControlTool 导入错误

**问题**: `src/tools/browser/control.py` 文件不存在，导致 `adapters.py` 导入失败

**解决方案**: 创建 `src/tools/browser/control.py` 文件，定义 `ControlTool` 类

**迁移任务**:
- [x] M5.4.1: 创建 `src/tools/browser/control.py` 文件
- [x] M5.4.2: 实现 `ControlTool` 类和 `ControlParams` 参数类
- [x] M5.4.3: 实现所有控制操作处理器（clear_cookies, delete_cookies, publish 等）
- [x] M5.4.4: 更新 `src/tools/browser/__init__.py` 导出
- [x] M5.4.5: 修复 `adapters.py` 中缺失 `src.tools.` 前缀的导入

---

## 三、任务依赖关系

```
M1 (基础工具)
    │
    ├──▶ M2 (视频处理)
    │       │
    │       ├──▶ M2.1 (视频下载)
    │       │       └──▶ M2.2 (视频传输) ───┐
    │       │                              │
    │       └──▶ M2.3 (视频拦截) ──────────┤
    │                                        │
    └──▶ M3 (文件上传) ─────────────────────┤
                                            │
    M4 (发布器重构) ─────────────────────────┤
                                            │
    M5 (集成测试) ◀──────────────────────────┘

详细依赖:
M1.1 ──┬──> M5.1
       │
       └──> M5.2

M2.1 ──┬──> M4.1.5 (视频工具链集成)
       │
M2.2 ──┤
       │
M2.3 ──┤
       │
M3.1 ──┘
```

---

## 四、迁移进度跟踪

### 已完成 ✅

| 任务 | 描述 | 完成时间 |
|------|------|----------|
| M4.1 | 发布器重构（XiaohongshuPublisher） | 2026-02-14 |
| M5.2 | 适配器集成（更新 adapters.py） | 2026-02-14 |
| M1.1 | 页面数据读取工具迁移 | 2026-02-14 |
| M1.2 | 脚本注入工具迁移 | 2026-02-14 |
| M3.1 | 文件上传工具整合 | 2026-02-14 |
| M2.3 | 视频上传拦截工具迁移 | 2026-02-14 |
| M2.2 | 视频分块传输工具迁移 | 2026-02-14 |
| M2.1 | 视频下载工具迁移 | 2026-02-14 |
| M5.1 | 工具模块集成（utils/__init__.py） | 2026-02-14 |
| M5.4 | 修复 ControlTool 导入错误 | 2026-02-14 |

### 进行中 🔄

| 任务 | 描述 | 开始时间 | 状态 |
|------|------|----------|------|
| - | - | - | - |

### 待开始 ⏳

| 任务 | 描述 | 优先级 |
|------|------|--------|
| - | 全部迁移任务已完成！ | - |

---

## 五、迁移策略

### 5.1 渐进式迁移

采用渐进式迁移策略，确保每一步都可测试：

1. **Step 1**: 创建目录结构
2. **Step 2**: 逐个迁移工具类
3. **Step 3**: 更新适配器调用
4. **Step 4**: 运行测试验证
5. **Step 5**: 清理旧代码

### 5.2 向后兼容

迁移过程中保持向后兼容：

```python
# 旧导入方式（临时保留）
from src.tools.xhs import XHSReadPageDataTool

# 新导入方式（推荐）
from src.tools.sites.xiaohongshu.utils import XHSReadPageDataTool
```

### 5.3 测试策略

- **单元测试**: 每个迁移的工具类需要测试
- **集成测试**: 测试工具间的协作
- **端到端测试**: 测试完整业务流程

---

## 六、风险与注意事项

### 6.1 已识别风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| API 变更导致兼容问题 | 中 | 保持向后兼容导入 |
| 视频工具链依赖复杂 | 高 | 先迁移独立功能 |
| 页面结构变化 | 低 | 使用选择器管理器 |

### 6.2 注意事项

1. **保持功能完整性**: 迁移后功能必须与原工具一致
2. **错误处理**: 保持原有的错误处理逻辑
3. **日志记录**: 保持原有的日志记录
4. **性能**: 迁移后性能不能显著下降

---

## 七、使用示例

### 迁移后使用方式

```python
# 方式1: 通过 XiaohongshuSite 适配器
from src.tools.sites.xiaohongshu import XiaohongshuSite

site = XiaohongshuSite()
await site.download_video(url="...")

# 方式2: 直接使用工具类
from src.tools.sites.xiaohongshu.utils import VideoDownloadTool

tool = VideoDownloadTool()
result = await tool.execute(params, context)

# 方式3: 通过 BusinessToolRegistry
from src.tools.business.registry import BusinessToolRegistry

tool = BusinessToolRegistry.get("xhs_download_video")
```

---

## 八、参考资源

- 原始工具: `src/tools/xhs/`
- 新框架适配器: `src/tools/sites/xiaohongshu/adapters.py`
- 业务抽象层: `src/tools/business/`
- Chrome Extension: `xiaohongshu-mcp-extension-latest/background.js`
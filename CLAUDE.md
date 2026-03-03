# CLAUDE.md

项目技术文档 - 浏览器自动化系统 (SilentAgent)

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Relay 服务（扩展模式必须）
python src/relay_server.py

# 启动 API 服务
uvicorn src.api.app:app --host 0.0.0.0 --port 8080 --reload
```

## 项目结构

```
src/
├── api/           # FastAPI REST 接口
├── browser/      # 浏览器客户端（Extension/Puppeteer/Hybrid）
├── client/       # Python 客户端
├── config.py     # 配置
├── flow/         # 工作流引擎
├── relay_server.py  # WebSocket 中继服务
└── tools/        # 工具框架和业务适配器
    ├── business/     # 业务逻辑基类
    │   └── selectors/ # 选择器版本管理
    └── sites/        # 网站适配器
        └── selectors/ # 通用选择器定义（分页/弹窗/搜索等）
extension/       # Chrome 扩展
```

## 浏览器模式

| 模式 | 说明 | 启动条件 |
|------|------|----------|
| `extension` | Chrome 扩展 | Relay 服务运行 |
| `puppeteer` | Puppeteer 控制 | Chrome 浏览器（自动） |
| `hybrid` | 混合模式 | 两者都运行 |

详细配置见 [.claude/rule/browser.md](.claude/rule/browser.md)

## 常用命令

| 任务 | 命令 |
|------|------|
| API 测试 | `pytest tests_api.py` |
| RPA 测试 | `pytest tests_xiaohongshu.py` |
| 浏览器测试 | `BROWSER_MODE=puppeteer python test_browser_client.py` |

详细测试说明见 [.claude/rule/testing.md](.claude/rule/testing.md)

## 架构要点

- **多插件系统**: 每个 Chrome 实例有唯一 `secret_key`，支持单客户端控制多浏览器
- **通信流程**: Python Client → Relay Server → Chrome Extension
- **无障碍树**: Puppeteer 模式使用真实 CDP accessibility tree
- **选择器抽象**: `sites/selectors/common.py` 定义通用选择器（分页/弹窗/搜索等），新网站只需继承并扩展特定字段

## 开发规范

- API 开发见 [.claude/rule/api.md](.claude/rule/api.md)
- 工具基类: `src/tools/tool.py`
- 业务适配器: `src/tools/business/`
- 网站选择器: `src/tools/sites/`（继承 `sites/selectors/common.py` 通用选择器）

# Browser Automation Rules

## 启动服务

```bash
# 启动 Relay server（Extension 模式必须）
python src/relay_server.py
python src/relay_server.py --port 18792  # 自定义端口
```

## 浏览器模式

| 模式 | 环境变量 | 说明 |
|------|----------|------|
| Extension | `BROWSER_MODE=extension` | Chrome 扩展模式（默认） |
| Puppeteer | `BROWSER_MODE=puppeteer` | Puppeteer 控制 |
| Hybrid | `BROWSER_MODE=hybrid` | 混合模式 |

## 环境变量

```bash
# 浏览器模式
BROWSER_MODE=extension|puppeteer|hybrid

# Puppeteer 配置
PUPPETEER_HEADLESS=true|false
PUPPETEER_ARGS=--arg1,--arg2
STEALTH_ENABLED=true|false

# Extension 配置
RELAY_HOST=127.0.0.1
RELAY_PORT=18792
SECRET_KEY=your_key
```

## 代码位置

- 工厂: `src/browser/client_factory.py`
- 基类: `src/browser/base.py`
- Extension: `src/browser/extension_client.py`
- Puppeteer: `src/browser/puppeteer_client.py`
- Hybrid: `src/browser/hybrid_client.py`
- 实例: `src/browser/instance.py`
- 管理器: `src/browser/manager.py`

## 多浏览器实例

支持同时运行多个浏览器实例，通过 `BrowserManager` 管理：

```python
from src.browser import BrowserManager, BrowserInstance, BrowserMode

# 创建实例
instance = BrowserInstance(
    mode=BrowserMode.HYBRID,
    secret_key="xxx",
    ws_endpoint="ws://...",
)

# 注册
instance_id = BrowserManager.register_instance(instance)

# 获取客户端
client = await BrowserManager.get_client(instance_id)
```

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/browser/register` | 注册实例 |
| GET | `/api/v1/browser/list` | 列出实例 |
| DELETE | `/api/v1/browser/{id}` | 注销实例 |
| GET | `/api/v1/browser/{id}/health` | 健康检查 |
| POST | `/api/v1/browser/{id}/set-default` | 设置默认 |

### 执行时指定实例

```bash
# 使用指定浏览器实例执行
curl -X POST http://localhost:8080/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{"tool": "xhs_list_feeds", "browser_id": "xxx-xxx-xxx"}'
```

## 无障碍树

| 模式 | 树类型 |
|------|--------|
| extension | 模拟 (DOM) |
| puppeteer | 真实 (CDP) |
| hybrid | 真实 (CDP) |

强制使用真实树: `await get_a11y_tree(use_real_tree=True)`

# Testing Rules

## 测试模式

```bash
# API 测试
pytest tests_api.py

# 小红书 RPA 测试
pytest tests_xiaohongshu.py

# 简单测试
python test_simple.py


```

## 测试要求

- Extension 模式测试需要 Chrome 扩展加载并连接 Relay server
- Extension 需要在设置中授权目标站点
- Puppeteer 模式需要 `puppeteer-extra` 包
- 参考 `test_a11y_tree.py` 和 `test_browser_client.py` 示例

## 快速验证

```bash
# 启动 Relay server（后台运行）
python src/relay_server.py &

# 启动 API 服务
uvicorn src.api.app:app --host 0.0.0.0 --port 8080 --reload
```

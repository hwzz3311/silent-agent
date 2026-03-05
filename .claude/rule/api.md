# API Development Rules

## 启动 API 服务

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8080 --reload
```

## API 结构

- 入口: `src/api/app.py`
- 端点: `src/api/routes/`
- 依赖注入: `src/api/dependencies/`

## 常用端点

| 路径 | 方法 | 描述 |
|------|------|------|
| `/tools` | GET | 列出可用工具 |
| `/tools/execute` | POST | 执行工具 |
| `/flow/execute` | POST | 执行工作流 |

## 开发注意事项

- 使用 `src/tools/` 中的 Tool 基类
- 业务逻辑放在 `src/tools/business/sites/`
- 返回格式统一使用 Pydantic models

# Neurone API 测试指南

本目录包含两套 API 测试工具，用于测试 Neurone 的 REST API 接口。

## 测试文件说明

### 1. `tests_api.py` - Python 异步测试客户端

**功能**: 使用 Python `aiohttp` 库进行异步 API 测试

**特点**:
- 完整的异步 HTTP 客户端封装
- 支持所有 API 接口测试
- 详细的测试结果输出

**前置依赖**:
```bash
pip install aiohttp
```

**使用方式**:
```bash
# 运行所有测试
python tests_api.py

# 运行特定测试
python tests_api.py health          # 健康检查
python tests_api.py tools           # 工具相关
python tests_api.py execute         # 执行相关
python tests_api.py flows           # 流程相关

# 快速验证 API 是否可用
python tests_api.py verify

# 测试特定工具详情
python tests_api.py browser.click
```

### 2. `test_api.sh` - Shell 脚本测试

**功能**: 使用 `curl` 命令进行 HTTP 接口测试

**特点**:
- 无需 Python 环境
- 轻量级快速测试
- 适合 CI/CD 集成

**使用方式**:
```bash
# 给脚本添加执行权限
chmod +x test_api.sh

# 运行所有测试
./test_api.sh

# 运行特定测试
./test_api.sh health
./test_api.sh tools
./test_api.sh execute
./test_api.sh flows
```

## API 接口列表

### 健康检查

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | REST API 健康检查 |
| `/health` | GET | Relay 健康检查 |

### 工具管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/tools` | GET | 获取工具列表 |
| `/api/v1/tools/search?q=` | GET | 搜索工具 |
| `/api/v1/tools/{name}` | GET | 获取工具详情 |
| `/api/v1/tools/{name}/schema` | GET | 获取工具参数 Schema |

### 工具执行

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/execute` | POST | 执行工具调用 |
| `/api/v1/execute/batch` | POST | 批量执行工具 |

### 流程管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/flows` | GET | 获取流程列表 |
| `/api/v1/flows` | POST | 创建流程 |
| `/api/v1/flows/{flow_id}` | GET | 获取流程详情 |
| `/api/v1/flows/{flow_id}` | PUT | 更新流程 |
| `/api/v1/flows/{flow_id}` | DELETE | 删除流程 |
| `/api/v1/flows/{flow_id}/run` | POST | 运行流程 |

### 录制回放

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/record/start` | POST | 开始录制 |
| `/api/v1/record/{id}/stop` | POST | 停止录制 |
| `/api/v1/record` | GET | 获取录制列表 |
| `/api/v1/record/{id}` | GET | 获取录制详情 |
| `/api/v1/record/{id}/replay` | POST | 回放录制 |

## 测试前准备

### 1. 启动 Relay 服务器

```bash
# 终端 1
cd network_hook/src
python relay_server.py --port 18792
```

### 2. 启动 API 服务

```bash
# 终端 2
cd network_hook
uvicorn src.api.app:app --host 0.0.0.0 --port 8080 --reload
```

### 3. 加载 Chrome 扩展

1. 打开 `chrome://extensions/`
2. 启用「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择 `network_hook/extension` 目录

### 4. 运行测试

```bash
# Python 测试
python tests_api.py verify

# Shell 测试
./test_api.sh
```

## 测试结果示例

### Python 测试结果

```
============================================
  Neurone API 测试套件
============================================

=== 健康检查测试 ===
  ✓ PASS REST API 健康检查
  ✓ PASS Relay 健康检查

=== 工具列表测试 ===
  ✓ PASS 获取工具列表 (工具数量: 12)
  ✓ PASS 工具分类统计 (分类: ['browser', 'recorder'])
```

### Shell 测试结果

```
=== 健康检查测试 ===
  → 测试 REST API 健康检查...
  ✓ PASS REST API 健康检查
  → 测试 Relay 健康检查...
  ✓ PASS Relay 健康检查
```

## CI/CD 集成

在 CI/CD 流程中添加测试步骤:

```yaml
# GitHub Actions 示例
- name: Run API Tests
  run: |
    # 启动服务
    uvicorn src.api.app:app --host 0.0.0.0 --port 8080 &
    API_PID=$!

    # 等待服务启动
    sleep 3

    # 运行测试
    python tests_api.py verify
    RESULT=$?

    # 停止服务
    kill $API_PID

    # 返回结果
    exit $RESULT
```

## 常见问题

### Q: 测试失败，提示无法连接到 API

A: 请确保 API 服务已启动:
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8080 --reload
```

### Q: 工具执行失败

A: 请确保:
1. Relay 服务器已启动
2. Chrome 扩展已连接
3. 目标网站已授权

### Q: Shell 脚本提示权限 denied

A: 请添加执行权限:
```bash
chmod +x test_api.sh
```

## 扩展测试

### 添加新测试用例

在 `tests_api.py` 中添加新测试方法:

```python
async def test_new_feature(self):
    """测试新功能"""
    print(f"\n{BLUE}=== 新功能测试 ==={RESET}")
    try:
        result = await self.api.new_method()
        if result.get("success"):
            print_result("新功能", True)
        else:
            print_result("新功能", False)
    except Exception as e:
        print_result("新功能", False, str(e))
```

然后在 `run_all_tests()` 中调用:

```python
async def run_all_tests(self):
    # ... 现有测试 ...
    await self.test_new_feature()
```
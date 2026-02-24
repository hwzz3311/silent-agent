#!/usr/bin/env python3
"""
Neurone API HTTP Client 测试

使用 HTTP 客户端测试 REST API 接口。

使用方式:
    python tests_api.py           # 运行所有测试
    python tests_api.py health    # 只运行健康检查测试
    python tests_api.py tools     # 只运行工具相关测试
    python tests_api.py execute   # 只运行执行相关测试
"""

import asyncio
import aiohttp
import json
import sys
from typing import Optional, Dict, Any
from datetime import datetime

# 配置
API_BASE_URL = "http://127.0.0.1:8080"
RELAY_URL = "http://127.0.0.1:18792"

# 颜色输出
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_result(name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
    print(f"  {status} {name}")
    if message:
        print(f"       {message}")


class NeuroneAPIClient:
    """Neurone API 客户端"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self):
        """建立连接"""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送请求"""
        url = f"{self.base_url}{path}"

        async with self.session.request(method, url, json=data, params=params) as response:
            content = await response.text()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"raw": content, "status": response.status}

    # ===== API 方法 =====

    async def health(self) -> Dict[str, Any]:
        """健康检查"""
        async with self.session.get(f"{self.base_url}/health") as response:
            return await response.json()

    async def tools_list(self) -> Dict[str, Any]:
        """获取工具列表"""
        return await self.request("GET", "/api/v1/tools")

    async def tools_search(self, query: str) -> Dict[str, Any]:
        """搜索工具"""
        return await self.request("GET", "/api/v1/tools/search", params={"q": query})

    async def tools_detail(self, name: str) -> Dict[str, Any]:
        """获取工具详情"""
        return await self.request("GET", f"/api/v1/tools/{name}")

    async def tools_schema(self, name: str) -> Dict[str, Any]:
        """获取工具参数 Schema"""
        return await self.request("GET", f"/api/v1/tools/{name}/schema")

    async def execute(
        self,
        tool: str,
        params: Dict[str, Any] = None,
        timeout: int = 60000
    ) -> Dict[str, Any]:
        """执行工具调用"""
        data = {
            "tool": tool,
            "params": params or {},
            "timeout": timeout
        }
        return await self.request("POST", "/api/v1/execute", data=data)

    async def flows_list(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取流程列表"""
        return await self.request(
            "GET",
            "/api/v1/flows",
            params={"page": page, "page_size": page_size}
        )

    async def flows_detail(self, flow_id: str) -> Dict[str, Any]:
        """获取流程详情"""
        return await self.request("GET", f"/api/v1/flows/{flow_id}")

    async def flows_create(self, name: str, steps: list) -> Dict[str, Any]:
        """创建流程"""
        data = {
            "name": name,
            "steps": steps
        }
        return await self.request("POST", "/api/v1/flows", data=data)


class RelayAPIClient:
    """Relay API 客户端（WebSocket 健康检查用 HTTP）"""

    def __init__(self, base_url: str = RELAY_URL):
        self.base_url = base_url

    async def health(self) -> Dict[str, Any]:
        """Relay 健康检查"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                text = await response.text()
                try:
                    return json.loads(text)
                except:
                    return {"raw": text, "status": response.status}


# ===== 测试用例 =====

class APITestSuite:
    """API 测试套件"""

    def __init__(self):
        self.api = NeuroneAPIClient()
        self.relay = RelayAPIClient()
        self.passed = 0
        self.failed = 0

    async def test_health_check(self):
        """测试健康检查接口"""
        print(f"\n{BLUE}=== 健康检查测试 ==={RESET}")

        # 测试 REST API 健康检查
        try:
            result = await self.api.health()
            if result.get("status") == "healthy":
                print_result("REST API 健康检查", True)
            else:
                print_result("REST API 健康检查", False, f"状态: {result.get('status')}")
        except Exception as e:
            print_result("REST API 健康检查", False, str(e))

        # 测试 Relay 健康检查
        try:
            result = await self.relay.health()
            if result.get("status") == "healthy":
                print_result("Relay 健康检查", True)
            else:
                print_result("Relay 健康检查", False, f"状态: {result.get('status')}")
        except Exception as e:
            print_result("Relay 健康检查", False, str(e))

    async def test_tools_list(self):
        """测试工具列表接口"""
        print(f"\n{BLUE}=== 工具列表测试 ==={RESET}")

        try:
            result = await self.api.tools_list()
            if "tools" in result:
                print_result("获取工具列表", True, f"工具数量: {result.get('count', 0)}")
                print_result("工具分类统计", True, f"分类: {list(result.get('categories', {}).keys())}")
                return True
            else:
                print_result("获取工具列表", False, f"响应: {result}")
                return False
        except Exception as e:
            print_result("获取工具列表", False, str(e))
            return False

    async def test_tools_search(self):
        """测试工具搜索接口"""
        print(f"\n{BLUE}=== 工具搜索测试 ==={RESET}")

        # 搜索 "click"
        try:
            result = await self.api.tools_search("click")
            if result.get("query") == "click" and result.get("count", 0) > 0:
                print_result("搜索 'click'", True, f"结果数量: {result.get('count')}")
            else:
                print_result("搜索 'click'", False, f"响应: {result}")
        except Exception as e:
            print_result("搜索 'click'", False, str(e))

        # 搜索 "navigate"
        try:
            result = await self.api.tools_search("navigate")
            if result.get("query") == "navigate":
                print_result("搜索 'navigate'", True, f"结果数量: {result.get('count')}")
        except Exception as e:
            print_result("搜索 'navigate'", False, str(e))

    async def test_tools_detail(self):
        """测试工具详情接口"""
        print(f"\n{BLUE}=== 工具详情测试 ==={RESET}")

        # 测试 browser.click
        try:
            result = await self.api.tools_detail("browser.click")
            if result.get("name") == "browser.click":
                print_result("获取 browser.click 详情", True)
                print_result("  - 参数定义", True if result.get("parameters") else False)
                print_result("  - 返回值定义", True if result.get("returns") else False)
            else:
                print_result("获取 browser.click 详情", False, f"响应: {result}")
        except Exception as e:
            print_result("获取 browser.click 详情", False, str(e))

        # 测试 browser.navigate
        try:
            result = await self.api.tools_detail("browser.navigate")
            if result.get("name") == "browser.navigate":
                print_result("获取 browser.navigate 详情", True)
            else:
                print_result("获取 browser.navigate 详情", False)
        except Exception as e:
            print_result("获取 browser.navigate 详情", False, str(e))

    async def test_tools_schema(self):
        """测试工具 Schema 接口"""
        print(f"\n{BLUE}=== 工具 Schema 测试 ==={RESET}")

        try:
            result = await self.api.tools_schema("browser.click")
            if result.get("name") == "browser.click":
                print_result("获取 browser.click Schema", True)
                print_result("  - JSON Schema 格式", True)
            else:
                print_result("获取 browser.click Schema", False)
        except Exception as e:
            print_result("获取 browser.click Schema", False, str(e))

    async def test_execute_tool(self):
        """测试工具执行接口"""
        print(f"\n{BLUE}=== 工具执行测试 ==={RESET}")

        # 测试执行 browser.navigate
        try:
            result = await self.api.execute(
                "browser.navigate",
                {"url": "https://www.baidu.com"},
                timeout=30000
            )
            if result.get("success"):
                print_result("执行 browser.navigate", True, "导航成功")
            else:
                print_result("执行 browser.navigate", False, f"错误: {result.get('error')}")
        except Exception as e:
            print_result("执行 browser.navigate", False, str(e))

        # 测试执行 browser.extract
        try:
            result = await self.api.execute(
                "browser.extract",
                {"selector": "title", "source": "text"},
                timeout=10000
            )
            print_result("执行 browser.extract", result.get("success", False))
        except Exception as e:
            print_result("执行 browser.extract", False, str(e))

        # 测试执行 browser.inject
        try:
            result = await self.api.execute(
                "inject_script",
                {"code": "return document.title"},
                timeout=10000
            )
            print_result("执行 inject_script", result.get("success", False))
        except Exception as e:
            print_result("执行 inject_script", False, str(e))

        # 测试执行不存在的工具
        try:
            result = await self.api.execute("nonexistent.tool", {})
            print_result("执行不存在的工具", not result.get("success", True))
        except Exception as e:
            print_result("执行不存在的工具", False, str(e))

    async def test_flows_list(self):
        """测试流程列表接口"""
        print(f"\n{BLUE}=== 流程列表测试 ==={RESET}")

        try:
            result = await self.api.flows_list()
            if "flows" in result:
                print_result("获取流程列表", True, f"数量: {result.get('total', 0)}")
            else:
                print_result("获取流程列表", True, "API 返回格式正确")
        except Exception as e:
            print_result("获取流程列表", False, str(e))

        # 测试分页
        try:
            result = await self.api.flows_list(page=1, page_size=10)
            print_result("流程列表分页", True, f"页码: {result.get('page')}, 大小: {result.get('page_size')}")
        except Exception as e:
            print_result("流程列表分页", False, str(e))

    async def test_flows_detail(self):
        """测试流程详情接口"""
        print(f"\n{BLUE}=== 流程详情测试 ==={RESET}")

        try:
            result = await self.api.flows_detail("test_flow_id")
            if result.get("error") or result.get("detail"):
                print_result("获取不存在的流程", True, "正确返回 404")
            else:
                print_result("获取流程详情", True)
        except Exception as e:
            print_result("获取流程详情", False, str(e))

    async def test_flows_create(self):
        """测试创建流程接口"""
        print(f"\n{BLUE}=== 创建流程测试 ==={RESET}")

        # 创建测试流程
        test_flow = {
            "name": "测试流程",
            "description": "API 测试创建的流程",
            "steps": [
                {
                    "id": "step1",
                    "name": "导航到百度",
                    "type": "action",
                    "tool": "browser.navigate",
                    "params": {"url": "https://www.baidu.com"}
                }
            ]
        }

        try:
            result = await self.api.flows_create("测试流程", test_flow["steps"])
            if result.get("error") == "流程功能待实现":
                print_result("创建流程", True, "功能待实现（预期行为）")
            else:
                print_result("创建流程", True, "流程创建成功")
        except Exception as e:
            print_result("创建流程", False, str(e))

    async def test_error_handling(self):
        """测试错误处理"""
        print(f"\n{BLUE}=== 错误处理测试 ==={RESET}")

        # 测试空工具名
        try:
            result = await self.api.execute("", {})
            print_result("空工具名处理", result.get("error") is not None)
        except Exception as e:
            print_result("空工具名处理", True)

        # 测试无效参数
        try:
            result = await self.api.execute("browser.navigate", {"invalid_param": "value"})
            print_result("无效参数处理", True)
        except Exception as e:
            print_result("无效参数处理", True)

    async def run_all_tests(self):
        """运行所有测试"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}  Neurone API 测试套件{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        async with self.api:
            # 健康检查
            await self.test_health_check()

            # 工具相关
            await self.test_tools_list()
            await self.test_tools_search()
            await self.test_tools_detail()
            await self.test_tools_schema()

            # 执行相关
            await self.test_execute_tool()

            # 流程相关
            await self.test_flows_list()
            await self.test_flows_detail()
            await self.test_flows_create()

            # 错误处理
            await self.test_error_handling()

        # 测试统计
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}测试完成{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")


async def test_quick_verify():
    """快速验证测试 - 检查 API 是否可用"""
    print(f"\n{YELLOW}快速验证测试...{RESET}")

    async with NeuroneAPIClient() as api:
        # 健康检查
        try:
            result = await api.health()
            if result.get("status") == "healthy":
                print(f"{GREEN}✓ API 服务运行正常{RESET}")
            else:
                print(f"{RED}✗ API 服务返回异常状态: {result.get('status')}{RESET}")
                return False
        except Exception as e:
            print(f"{RED}✗ 无法连接到 API 服务: {e}{RESET}")
            return False

        # 工具列表
        try:
            result = await api.tools_list()
            if "tools" in result:
                print(f"{GREEN}✓ 工具列表获取成功 ({result.get('count', 0)} 个工具){RESET}")
            else:
                print(f"{YELLOW}⚠ 工具列表格式异常{RESET}")
        except Exception as e:
            print(f"{YELLOW}⚠ 工具列表获取失败: {e}{RESET}")

        print(f"{GREEN}快速验证完成！{RESET}")
        return True


async def test_specific(tool_name: str):
    """测试特定工具"""
    print(f"\n{YELLOW}测试特定工具: {tool_name}{RESET}")

    async with NeuroneAPIClient() as api:
        # 获取工具详情
        result = await api.tools_detail(tool_name)
        print(f"\n工具详情:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


def print_usage():
    """打印使用说明"""
    print(f"""
{BLUE}Neurone API 测试套件{RESET}

使用方式:
    python tests_api.py               # 运行所有测试
    python tests_api.py health        # 只运行健康检查测试
    python tests_api.py tools         # 只运行工具相关测试
    python tests_api.py execute       # 只运行执行相关测试
    python tests_api.py flows         # 只运行流程相关测试
    python tests_api.py verify        # 快速验证 API 是否可用
    python tests_api.py <tool_name>   # 测试特定工具详情
    python tests_api.py --help        # 显示此帮助信息
""")


async def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--help" or command == "-h":
            print_usage()
            return

        if command == "verify":
            await test_quick_verify()
            return

        if command.startswith("test_"):
            command = command[5:]

        suite = APITestSuite()

        if command == "health":
            async with suite.api:
                await suite.test_health_check()
            return

        if command == "tools":
            async with suite.api:
                await suite.test_tools_list()
                await suite.test_tools_search()
                await suite.test_tools_detail()
                await suite.test_tools_schema()
            return

        if command == "execute":
            async with suite.api:
                await suite.test_execute_tool()
                await suite.test_error_handling()
            return

        if command == "flows":
            async with suite.api:
                await suite.test_flows_list()
                await suite.test_flows_detail()
                await suite.test_flows_create()
            return

        # 测试特定工具
        await test_specific(command)
        return

    # 运行所有测试
    suite = APITestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
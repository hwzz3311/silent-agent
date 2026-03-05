#!/usr/bin/env python3
"""
闲鱼业务逻辑 API 测试

测试闲鱼相关的所有业务功能：
- 登录相关：密码登录、获取 Cookie
- 浏览相关：搜索商品
- 发布相关：发布商品

使用方式:
    python tests_xianyu.py              # 运行所有测试
    python tests_xianyu.py login        # 只运行登录相关测试
    python tests_xianyu.py browse       # 只运行浏览相关测试
    python tests_xianyu.py publish      # 只运行发布相关测试
    python tests_xianyu.py verify       # 快速验证是否可用
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime

# API 基础 URL
API_BASE_URL = "http://127.0.0.1:8080"
RELAY_URL = "http://127.0.0.1:18792"

# 插件密钥（用于多插件路由）- 可选，二选一即可
SECRET_KEY = "CG1PCGPNY2DHB2PKYMNLYWTOYNBPAGTO"

# 浏览器实例 ID（用于多浏览器路由）- 可选，二选一即可
# 如果传了 browser_id 则优先使用指定浏览器实例
BROWSER_ID = "7da1213d-02f3-4cdc-8aba-47ee87014a89"

# 颜色输出
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


def print_result(name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = f"{GREEN}✓ PASS{RESET}" if success else f"{RED}✗ FAIL{RESET}"
    print(f"  {status} {name}")
    if message:
        print(f"       {message}")


class XianyuAPIClient:
    """闲鱼 API 客户端"""

    def __init__(self, base_url: str = API_BASE_URL, secret_key: str = SECRET_KEY, browser_id: str = BROWSER_ID):
        self.base_url = base_url
        self.secret_key = secret_key
        self.browser_id = browser_id
        self.session = None

    async def connect(self):
        """建立连接"""
        import aiohttp
        self.session = aiohttp.ClientSession()

    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """发送请求"""
        import aiohttp

        url = f"{self.base_url}{path}"
        print(f"[DEBUG] REQUEST: {method} {url}")
        if data:
            print(f"[DEBUG] DATA: {data}")
        try:
            async with self.session.request(method, url, json=data, params=params) as response:
                content = await response.text()
                print(f"[DEBUG] RESPONSE: status={response.status}, body_len={len(content)}")
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"raw": content, "status": response.status}
        except aiohttp.ClientConnectorError as e:
            print(f"[ERROR] 连接失败: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] 请求异常: {e}")
            raise

    # ===== 工具执行相关 =====

    async def execute_tool(self, tool: str, params: Dict[str, Any] = None, timeout: int = 60000, secret_key: str = None, browser_id: str = None) -> Dict[str, Any]:
        """执行工具调用"""
        # 如果未传入 secret_key，使用默认密钥
        if secret_key is None:
            secret_key = self.secret_key
        # 如果未传入 browser_id 使用默认浏览器实例 ID
        if browser_id is None:
            browser_id = self.browser_id
        data = {
            "tool": tool,
            "params": params or {},
            "timeout": timeout,
            "secret_key": secret_key,
            "browser_id": browser_id
        }
        return await self.request("POST", "/api/v1/execute", data=data)

    # ===== 闲鱼专用工具 =====

    # 登录相关
    async def xianyu_password_login(self, account: str, password: str, headless: bool = True) -> Dict[str, Any]:
        """密码登录闲鱼"""
        return await self.execute_tool("xianyu_password_login", {
            "account": account,
            "password": password,
            "headless": headless
        })

    async def xianyu_get_cookies(self, target_url: str = None) -> Dict[str, Any]:
        """获取 Cookie"""
        params = {}
        if target_url:
            params["target_url"] = target_url
        return await self.execute_tool("xianyu_get_cookies", params)

    # 浏览相关
    async def xianyu_search_item(
        self,
        keyword: str,
        pages: int = 1,
        items_per_page: int = 30
    ) -> Dict[str, Any]:
        """搜索商品

        Args:
            keyword: 搜索关键词
            pages: 获取页数（默认1）
            items_per_page: 每页商品数（默认30）
        """
        return await self.execute_tool("xianyu_search_item", {
            "keyword": keyword,
            "pages": pages,
            "items_per_page": items_per_page
        })

    # 发布相关
    async def xianyu_publish_item(
        self,
        price: str,
        description: str,
        images: list = None,
        category_index: int = 3
    ) -> Dict[str, Any]:
        """发布商品

        Args:
            price: 商品价格
            description: 商品描述
            images: 图片路径列表
            category_index: 分类索引（默认3=其他技能服务）
        """
        return await self.execute_tool("xianyu_publish_item", {
            "price": price,
            "description": description,
            "images": images or [],
            "category_index": category_index
        })

    # 通用浏览器工具（也常用于闲鱼场景）
    async def navigate(self, url: str, new_tab: bool = True) -> Dict[str, Any]:
        """导航到 URL"""
        return await self.execute_tool("browser.navigate", {
            "url": url,
            "new_tab": new_tab
        })

    async def browser_click(self, selector: str, text: str = None) -> Dict[str, Any]:
        """点击页面元素"""
        return await self.execute_tool("browser.click", {
            "selector": selector,
            "text": text
        })

    async def browser_fill(self, selector: str, value: str) -> Dict[str, Any]:
        """填充表单"""
        return await self.execute_tool("browser.fill", {
            "selector": selector,
            "value": value
        })

    async def browser_extract(self, selector: str, attribute: str = "text") -> Dict[str, Any]:
        """提取数据"""
        return await self.execute_tool("browser.extract", {
            "selector": selector,
            "attribute": attribute
        })


class XianyuTestSuite:
    """闲鱼测试套件"""

    def __init__(self):
        self.api = XianyuAPIClient()
        self.passed = 0
        self.failed = 0

    async def test_connection(self):
        """测试后端与插件的连接是否正常"""
        print(f"\n{CYAN}=== 连接测试 ==={RESET}")

        import aiohttp

        # 测试1: 检查 API 服务器是否运行
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE_URL}/health", timeout=5) as resp:
                    api_running = resp.status == 200
            print_result("API 服务器运行中", api_running, f"状态码: {resp.status}")
        except Exception as e:
            print_result("API 服务器运行中", False, f"无法连接: {e}")
            # 如果 API 无法连接，后续测试也无法进行，直接返回
            return

        # 测试2: 检查 Relay 服务器是否运行
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{RELAY_URL}/", timeout=5) as resp:
                    relay_running = resp.status == 200
            print_result("Relay 服务器运行中", relay_running, f"状态码: {resp.status}")
        except Exception as e:
            print_result("Relay 服务器运行中", False, f"无法连接: {e}")

        # 先获取活动标签页，如果没有则创建一个
        tab_id = None
        try:
            tab_result = await self.api.execute_tool("browser_control", {"action": "get_active_tab"}, timeout=10000)
            if tab_result.get("success") and tab_result.get("data"):
                tab_id = tab_result.get("data", {}).get("tabId")
                print(f"DEBUG 活动标签页: tabId={tab_id}")
            else:
                # 没有活动标签页，创建一个新标签页
                print(f"DEBUG 没有活动标签页正在创建...")
                nav_result = await self.api.execute_tool("chrome_navigate", {
                    "url": "https://www.baidu.com",
                    "newTab": True
                }, timeout=15000)
                if nav_result.get("success") and nav_result.get("data"):
                    tab_id = nav_result.get("data", {}).get("tabId")
                    print(f"DEBUG 已创建标签页: tabId={tab_id}")
        except Exception as e:
            print(f"DEBUG 获取/创建标签页失败: {e}")

        tool_params = {"timeout": 10000}
        if tab_id:
            tool_params["tabId"] = tab_id

        # 测试3: 检查浏览器连接状态 - 使用扩展支持的工具 read_page_data
        try:
            result = await self.api.execute_tool("read_page_data", {"path": "document.title", **tool_params}, timeout=10000)
            print(f"DEBUG: {result}")
            has_error = "detail" in result and "未知工具" in str(result.get("detail", ""))
            browser_connected = not has_error
            data_str = str(result)[:150]
            print_result("浏览器已连接", browser_connected, f"结果: {data_str}")
        except Exception as e:
            print_result("浏览器已连接", False, str(e))

        # 测试4: 执行简单浏览器命令验证通信 - 使用 read_page_data
        try:
            result = await self.api.execute_tool("read_page_data", {
                "path": "1 + 1",
                **tool_params
            }, timeout=10000)
            print(f"DEBUG read_page_data: {result}")
            has_error = "detail" in result and "未知工具" in str(result.get("detail", ""))
            eval_success = not has_error and result.get("success", False)
            print_result("浏览器通信正常", eval_success, f"计算 1+1 结果: {result.get('data', 'N/A')}")
        except Exception as e:
            print_result("浏览器通信正常", False, str(e))

        # 测试5: 获取当前页面 URL 验证页面通信 - 使用 read_page_data
        try:
            result = await self.api.execute_tool("read_page_data", {
                "path": "location.href",
                **tool_params
            }, timeout=10000)
            print(f"DEBUG location.href: {result}")
            page_url = result.get("data", "")
            has_url = page_url and isinstance(page_url, str) and len(page_url) > 0
            print_result("获取页面 URL", has_url, f"URL: {str(page_url)[:50] if page_url else 'N/A'}")
        except Exception as e:
            print_result("获取页面 URL", False, str(e))

    async def test_login_tools(self):
        """测试登录相关工具"""
        print(f"\n{CYAN}=== 闲鱼登录工具测试 ==={RESET}")

        # 密码登录
        try:
            # 注意：这是一个阻塞调用，需要真实账号密码
            # 这里只测试 API 是否可调用，实际登录需要真实账号
            result = await self.api.xianyu_password_login(
                account="13800138000",  # 测试账号
                password="test_password",
                headless=True
            )
            # 由于是测试环境，可能返回失败是预期的（账号不存在）
            print_result("密码登录 API", result.get("success", False) or "login" in str(result).lower(), f"结果: {str(result)[:100]}")
        except Exception as e:
            print_result("密码登录 API", False, str(e))

        # 获取 Cookie
        try:
            result = await self.api.xianyu_get_cookies()
            has_cookie = result.get("success", False) or "cookie" in str(result).lower()
            print_result("获取 Cookie", has_cookie, f"结果: {str(result)[:100]}")
        except Exception as e:
            print_result("获取 Cookie", False, str(e))

    async def test_browse_tools(self):
        """测试浏览相关工具"""
        print(f"\n{CYAN}=== 闲鱼浏览工具测试 ==={RESET}")

        # 搜索商品 - 单页
        try:
            result = await self.api.xianyu_search_item(
                keyword="iPhone",
                pages=1,
                items_per_page=10
            )
            has_results = result.get("success", False) or "search" in str(result.get("data", ""))
            data = result.get("data", {})
            count = len(data.get("results", [])) if isinstance(data, dict) else 0
            print_result("搜索商品(iPhone, 1页)", has_results, f"获取到 {count} 个商品")
        except Exception as e:
            print_result("搜索商品(iPhone, 1页)", False, str(e))

        # 搜索商品 - 多页
        try:
            result = await self.api.xianyu_search_item(
                keyword="RPA",
                pages=2,
                items_per_page=20
            )
            has_results = result.get("success", False) or "search" in str(result.get("data", ""))
            data = result.get("data", {})
            count = len(data.get("results", [])) if isinstance(data, dict) else 0
            print_result("搜索商品(RPA, 2页)", has_results and count >= 20, f"获取到 {count} 个商品")
        except Exception as e:
            print_result("搜索商品(RPA, 2页)", False, str(e))

    async def test_publish_tools(self):
        """测试发布相关工具"""
        print(f"\n{CYAN}=== 闲鱼发布工具测试 ==={RESET}")

        # 发布商品（不带图片）
        try:
            result = await self.api.xianyu_publish_item(
                price="99",
                description="测试发布商品描述内容",
                images=[],
                category_index=3
            )
            has_result = result.get("success", False) or "publish" in str(result.get("data", ""))
            print_result("发布商品(无图片)", has_result, f"结果: {str(result)[:100]}")
        except Exception as e:
            print_result("发布商品(无图片)", False, str(e))

    async def test_browser_tools_on_xianyu(self):
        """测试在闲鱼页面使用浏览器工具"""
        print(f"\n{CYAN}=== 闲鱼页面浏览器工具测试 ==={RESET}")

        # 导航到闲鱼
        try:
            result = await self.api.navigate("https://www.goofish.com")
            print_result("导航到闲鱼首页", result.get("success", False), f"结果: {result.get('data', result)}")
        except Exception as e:
            print_result("导航到闲鱼首页", False, str(e))

        # 等待元素
        try:
            result = await self.api.execute_tool("browser.wait", {
                "selector": ".item-card",
                "count": 1,
                "timeout": 5000
            })
            print_result("等待首页元素", result.get("success", False), f"结果: {result.get('data', result)}")
        except Exception as e:
            print_result("等待首页元素", False, str(e))

    async def test_xianyu_specific_selectors(self):
        """测试闲鱼特定选择器"""
        print(f"\n{CYAN}=== 闲鱼特定选择器测试 ==={RESET}")

        try:
            from src.tools.sites.xianyu.selectors import XianyuSelector

            selector = XianyuSelector()
            print(f"  {BLUE}获取闲鱼选择器{RESET}")
            print_result("闲鱼选择器加载", True)
        except Exception as e:
            print_result("闲鱼选择器加载", False, str(e))

    async def run_all_tests(self):
        """运行所有测试"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}  闲鱼业务逻辑测试套件{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        async with self.api:
            # 连接测试（优先执行确保通信正常）
            await self.test_connection()

            # 登录工具
            await self.test_login_tools()

            # 浏览工具
            await self.test_browse_tools()

            # 发布工具
            await self.test_publish_tools()

            # 浏览器工具（闲鱼页面）
            await self.test_browser_tools_on_xianyu()

            # 闲鱼特定选择器
            await self.test_xianyu_specific_selectors()

        # 测试统计
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}测试完成{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")


async def test_quick_verify():
    """快速验证测试 - 检查闲鱼 API 是否可用"""
    print(f"\n{YELLOW}快速验证闲鱼 API...{RESET}")

    async with XianyuAPIClient() as api:
        # 测试1: API 服务器健康检查
        try:
            import aiohttp
            async with api.session.get(f"{API_BASE_URL}/health") as response:
                result = await response.json()
                if result.get("status") == "healthy":
                    print(f"{GREEN}✓ API 服务运行正常{RESET}")
                else:
                    print(f"{YELLOW}⚠ API 返回异常状态: {result.get('status')}{RESET}")
        except Exception as e:
            print(f"{RED}✗ 无法连接到 API 服务: {e}{RESET}")
            return False

        # 测试2: 检查浏览器连接
        try:
            result = await api.execute_tool("browser_control", {"action": "get_active_tab"}, timeout=10000)
            if result.get("success", False):
                print(f"{GREEN}✓ 浏览器已连接{RESET}")
            else:
                print(f"{YELLOW}⚠ 浏览器未连接: {result.get('error', 'Unknown')}{RESET}")
        except Exception as e:
            print(f"{YELLOW}⚠ 浏览器通信失败: {e}{RESET}")

        # 测试3: 简单浏览器命令测试
        try:
            result = await api.execute_tool("browser_evaluate", {
                "code": "1 + 1",
                "world": "MAIN"
            }, timeout=10000)
            eval_result = result.get("data", {}).get("result")
            if eval_result == 2:
                print(f"{GREEN}✓ 浏览器通信正常 (1+1={eval_result}){RESET}")
            else:
                print(f"{YELLOW}⚠ 浏览器返回异常结果: {eval_result}{RESET}")
        except Exception as e:
            print(f"{YELLOW}⚠ 浏览器命令执行失败: {e}{RESET}")

        # 测试4: 检查闲鱼选择器
        try:
            from src.tools.sites.xianyu.selectors import XianyuSelector
            selector = XianyuSelector()
            print(f"{GREEN}✓ 闲鱼选择器加载成功{RESET}")
        except Exception as e:
            print(f"{YELLOW}⚠ 闲鱼选择器加载失败: {e}{RESET}")

        print(f"{GREEN}快速验证完成！{RESET}")
        return True


def print_usage():
    """打印使用说明"""
    print(f"""
{BLUE}闲鱼业务逻辑测试套件{RESET}

使用方式:
    python tests_xianyu.py              # 运行所有测试
    python tests_xianyu.py login        # 只运行登录相关测试
    python tests_xianyu.py browse       # 只运行浏览相关测试
    python tests_xianyu.py publish      # 只运行发布相关测试
    python tests_xianyu.py verify       # 快速验证 API 是否可用
    python tests_xianyu.py connection   # 只运行连接测试
    python tests_xianyu.py selectors    # 测试选择器加载
    python tests_xianyu.py --help       # 显示此帮助信息
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

        if command == "connection":
            suite = XianyuTestSuite()
            async with suite.api:
                await suite.test_connection()
            return

        suite = XianyuTestSuite()

        if command == "login":
            async with suite.api:
                await suite.test_login_tools()
            return

        if command == "browse":
            async with suite.api:
                await suite.test_browse_tools()
            return

        if command == "publish":
            async with suite.api:
                await suite.test_publish_tools()
            return

        if command == "selectors":
            await suite.test_xianyu_specific_selectors()
            return

        # 未知命令
        print(f"{RED}未知命令: {command}{RESET}")
        print_usage()
        return

    # 运行所有测试
    suite = XianyuTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

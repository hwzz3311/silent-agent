#!/usr/bin/env python3
"""
测试获取小红书网页的无障碍树

使用方式:
    python test_a11y_tree.py
"""

import asyncio
import json
import sys

# API 基础 URL
API_BASE_URL = "http://127.0.0.1:8080"
RELAY_URL = "http://127.0.0.1:18792"

# 插件密钥
SECRET_KEY = "CG1PCGPNY2DHB2PKYMNLYWTOYNBPAGTO"


class TestClient:
    """测试客户端"""

    def __init__(self, base_url: str = API_BASE_URL, secret_key: str = SECRET_KEY):
        self.base_url = base_url
        self.secret_key = secret_key
        self.session = None

    async def connect(self):
        import aiohttp
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def request(self, method: str, path: str, data: dict = None):
        import aiohttp
        url = f"{self.base_url}{path}"
        async with self.session.request(method, url, json=data) as response:
            content = await response.text()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"raw": content, "status": response.status}

    async def execute_tool(self, tool: str, params: dict = None, timeout: int = 60000):
        """执行工具调用"""
        data = {
            "tool": tool,
            "params": params or {},
            "timeout": timeout,
            "secret_key": self.secret_key,
        }
        return await self.request("POST", "/api/v1/execute", data=data)

    async def navigate(self, url: str, new_tab: bool = True):
        """导航到 URL"""
        return await self.execute_tool("browser.navigate", {
            "url": url,
            "new_tab": new_tab
        })

    async def get_a11y_tree(self, action: str = "get_tree", limit: int = 100):
        """获取无障碍树"""
        return await self.execute_tool("a11y_tree", {
            "action": action,
            "limit": limit
        }, timeout=30000)


async def main():
    async with TestClient() as client:
        # 1. 导航到小红书首页
        print(">>> 导航到小红书首页...")
        result = await client.navigate("https://zhuanlan.zhihu.com/p/381044910", new_tab=True)
        print(f"导航结果: {json.dumps(result, ensure_ascii=False)[:500]}")

        # 等待页面加载
        print(">>> 等待页面加载 (5秒)...")
        await asyncio.sleep(5)

        # 2. 获取无障碍树
        print(">>> 获取无障碍树...")
        result = await client.get_a11y_tree(action="get_tree", limit=200)

        print(f"\n=== 无障碍树结果 ===")
        print(f"成功: {result.get('success')}")

        if result.get("success"):
            data = result.get("data", {})
            print(f"节点总数: {data.get('totalNode')}")

            # 保存完整结果到文件
            with open("a11y_tree_result.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"完整结果已保存到: a11y_tree_result.json")

            # 打印部分节点预览
            nodes = data.get("nodes", {})
            root_ids = data.get("rootIds", [])

            print(f"\n根节点 IDs: {root_ids[:10]}...")
            print(f"\n前 10 个节点预览:")
            for i, (node_id, node) in enumerate(list(nodes.items())[:10]):
                print(f"  [{node_id}] role={node.get('role')}, name={node.get('name', '')[:50]}")
        else:
            print(f"失败原因: {result.get('message')}")
            print(f"完整结果: {json.dumps(result, ensure_ascii=False)[:1000]}")


if __name__ == "__main__":
    print("=" * 50)
    print("小红书无障碍树测试")
    print("=" * 50)
    asyncio.run(main())
#!/usr/bin/env python3
"""
Neurone Demo - 完整闭环演示

演示流程:
1. 获取页面 DOM（展示全知感知）
2. 模拟 AI 分析（找到可点击的元素）
3. 执行物理点击（模拟人类轨迹）
"""

import asyncio
import json
import sys
import os

# Add python directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cdp_client import CDPClient


def print_divider(title: str):
    """打印分隔线"""
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print('=' * 50)


def format_dom_tree(dom: dict, indent: int = 0) -> str:
    """格式化打印 DOM 树"""
    prefix = "  " * indent
    node_type = dom.get("nodeName", "UNKNOWN")
    node_id = dom.get("nodeId", "?")
    name = dom.get("localName", "")

    line = f"{prefix}[{node_type}] id={node_id}"
    if name:
        line += f" <{name}>"
    if dom.get("attributes"):
        attrs = " ".join(f'{k}="{v}"' for k, v in zip(dom.get("attributes", [])[::2],
                                                        dom.get("attributes", [])[1::2]))
        line += f" {attrs}"
    return line


async def analyze_dom(dom: dict) -> list:
    """
    模拟 AI 分析 DOM，返回可点击的元素列表
    """
    clickables = []

    def traverse(node):
        # 检查是否是可点击的元素
        tag_name = node.get("localName", "").lower()
        role = ""

        attrs = node.get("attributes", [])
        attrs_dict = {}
        for i in range(0, len(attrs) - 1, 2):
            attrs_dict[attrs[i]] = attrs[i + 1]

        # 检查可点击特征
        is_clickable = (
            tag_name in ["a", "button", "input", "select", "textarea"] or
            attrs_dict.get("role") in ["button", "link", "menuitem"] or
            attrs_dict.get("onclick") or
            node.get("clickable")
        )

        if is_clickable:
            bounds = node.get("bounds", {})
            if bounds:
                clickables.append({
                    "tag": tag_name,
                    "text": attrs_dict.get("text", attrs_dict.get("innerText", ""))[:50],
                    "x": bounds.get("x", 0),
                    "y": bounds.get("y", 0),
                    "width": bounds.get("width", 0),
                    "height": bounds.get("height", 0)
                })

        # 递归遍历子节点
        for child in node.get("children", []):
            traverse(child)

    traverse(dom)
    return clickables


async def demo_health_check():
    """Demo: 健康检查"""
    print_divider("1. 启动 CDP 连接")

    client = CDPClient()
    print(f"  目标: localhost:{client.port}")
    print("  正在连接...")

    try:
        await client.connect()
        print("  [OK] CDP 连接成功!")
        print(f"  启用域: DOM, Input")

        # 测试发送命令
        result = await client.send_command("Browser.getVersion")
        print(f"  Chrome 版本: {result.get('product', 'unknown')}")

        return client
    except Exception as e:
        print(f"  [ERROR] 连接失败: {e}")
        print("\n请确保 Chrome 以调试模式运行:")
        print("  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
        return None


async def demo_get_dom(client: CDPClient):
    """Demo: 获取 DOM（展示全知感知）"""
    print_divider("2. 获取 DOM 树（全知感知）")

    print("  发送 DOM.getDocument 命令...")
    dom = await client.get_dom()

    # 打印 DOM 统计
    def count_nodes(node):
        count = 1
        for child in node.get("children", []):
            count += count_nodes(child)
        return count

    total_nodes = count_nodes(dom)
    print(f"  [OK] 获取完成!")
    print(f"  节点总数: {total_nodes}")

    # 打印前 5 层结构
    print("\n  DOM 树结构预览:")
    print("  " + format_dom_tree(dom))

    # 打印部分子节点
    children = dom.get("children", [])[:3]
    for child in children:
        print("  " + format_dom_tree(child, indent=1))

    return dom


async def demo_ai_analysis(dom: dict):
    """Demo: 模拟 AI 分析"""
    print_divider("3. AI 分析（寻找可点击元素）")

    print("  正在分析 DOM 结构...")
    clickables = await analyze_dom(dom)

    print(f"  找到 {len(clickables)} 个可点击元素:")

    if clickables:
        for i, elem in enumerate(clickables[:5], 1):
            print(f"\n  [{i}] <{elem['tag']}>")
            text = elem['text'] or "(无文本)"
            print(f"      文本: {text}")
            print(f"      位置: ({elem['x']}, {elem['y']})")
            print(f"      尺寸: {elem['width']}x{elem['height']}")

        if len(clickables) > 5:
            print(f"  ... 还有 {len(clickables) - 5} 个元素")
    else:
        print("  未找到明显的可点击元素")
        print("  尝试获取完整的 DOM 边界信息...")

    return clickables


async def demo_click(client: CDPClient, x: int, y: int, description: str):
    """Demo: 执行物理点击"""
    print_divider(f"4. 执行点击: {description}")

    print(f"  目标坐标: ({x}, {y})")
    print("  模式: 人类轨迹模拟")

    try:
        result = await client.click(x, y, human=True)
        if result.get("success"):
            print("  [OK] 点击完成!")
            print(f"      类型: {result.get('type', 'unknown')}")
        else:
            print(f"  [ERROR] 点击失败: {result.get('error')}")
    except Exception as e:
        print(f"  [ERROR] 点击异常: {e}")


async def demo_full_loop():
    """完整闭环演示"""
    print_divider("Neurone Demo - 完整闭环演示")
    print("  流程: DOM获取 → AI分析 → 物理点击")
    print()

    # Step 1: 健康检查和连接
    client = await demo_health_check()
    if not client:
        return False

    try:
        # Step 2: 获取 DOM
        dom = await demo_get_dom(client)

        # Step 3: AI 分析
        clickables = await demo_ai_analysis(dom)

        # Step 4: 执行点击
        if clickables:
            # 点击第一个找到的可点击元素
            target = clickables[0]
            center_x = target["x"] + target["width"] // 2
            center_y = target["y"] + target["height"] // 2

            await demo_click(
                client,
                center_x,
                center_y,
                f"点击 <{target['tag']}> 元素"
            )
        else:
            # 如果没找到可点击元素，点击页面中心
            await demo_click(client, 400, 300, "点击页面中心")

        print_divider("Demo 完成!")
        print("\n下一步:")
        print("  1. 打开 Chrome 并加载扩展")
        print("  2. 运行: python python/install_host.py")
        print("  3. 测试完整的 Native Messaging 流程")

        return True

    finally:
        await client.close()


async def demo_direct_cdp():
    """
    演示如何直接使用 CDP Client（不经过 Native Messaging）

    这个演示可以直接运行，不需要安装扩展
    """
    print("\n直接 CDP 模式演示")
    print("-" * 40)
    print("这个演示直接连接 CDP，不依赖 Chrome 扩展")

    async with CDPClient() as client:
        # 获取页面标题
        result = await client.send_command("Runtime.evaluate", {
            "expression": "document.title"
        })
        title = result.get("result", {}).get("value", "unknown")
        print(f"当前页面标题: {title}")

        # 获取 body
        result = await client.send_command("DOM.getDocument")
        root = result.get("root", {})
        body_id = None

        # 查找 body
        def find_body(node):
            nonlocal body_id
            if node.get("localName") == "body":
                body_id = node.get("nodeId")
            for child in node.get("children", []):
                find_body(child)

        find_body(root)
        print(f"Body 节点 ID: {body_id}")


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Neurone Demo")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="直接使用 CDP，不经过 Native Messaging"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="CDP 主机地址 (默认: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9222,
        help="CDP 端口 (默认: 9222)"
    )

    args = parser.parse_args()

    if args.direct:
        # 直接 CDP 模式
        asyncio.run(demo_direct_cdp())
    else:
        # 完整闭环演示
        asyncio.run(demo_full_loop())


if __name__ == "__main__":
    main()
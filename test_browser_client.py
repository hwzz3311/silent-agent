#!/usr/bin/env python3
"""
测试浏览器客户端模块

测试多种浏览器客户端模式的创建和基本功能。

使用方式:
    # 测试扩展模式
    BROWSER_MODE=extension python test_browser_client.py

    # 测试 Puppeteer 模式
    BROWSER_MODE=puppeteer python test_browser_client.py

    # 测试混合模式
    BROWSER_MODE=hybrid python test_browser_client.py
"""

import asyncio
import os
import sys

# 设置当前目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.browser import BrowserClientFactory, BrowserMode
from src.config import get_config, set_config, AppConfig, BrowserSettings


async def test_client_creation():
    """测试客户端创建"""
    print("=" * 50)
    print("测试浏览器客户端创建")
    print("=" * 50)

    # 读取配置
    config = get_config()
    print(f"当前配置: mode={config.browser.mode.value}")
    print(f"  puppeteer_headless: {config.browser.puppeteer_headless}")
    print(f"  stealth_enabled: {config.browser.stealth_enabled}")
    print(f"  relay_host: {config.browser.relay_host}")
    print(f"  relay_port: {config.browser.relay_port}")

    # 创建客户端
    client = BrowserClientFactory.create_client()
    print(f"客户端类型: {type(client).__name__}")

    return client


async def test_client_connection(client):
    """测试客户端连接"""
    print("\n" + "=" * 50)
    print("测试客户端连接")
    print("=" * 50)

    try:
        await client.connect()
        print(f"连接状态: {client.is_connected}")
    except Exception as e:
        print(f"连接失败: {e}")
        # 对于 extension 模式可能是正常的（没有扩展连接）
        return False

    return client.is_connected


async def test_navigate(client):
    """测试导航功能"""
    print("\n" + "=" * 50)
    print("测试导航功能")
    print("=" * 50)

    if not client.is_connected:
        print("跳过：客户端未连接")
        return

    try:
        result = await client.navigate("https://www.example.com", new_tab=True)
        print(f"导航结果: {result}")
    except Exception as e:
        print(f"导航失败: {e}")


async def test_a11y_tree(client):
    """测试无障碍树获取"""
    print("\n" + "=" * 50)
    print("测试无障碍树获取")
    print("=" * 50)

    if not client.is_connected:
        print("跳过：客户端未连接")
        return

    try:
        result = await client.get_a11y_tree(action="get_tree", limit=50)
        print(f"获取结果: success={result.get('success', False)}")

        if result.get('success'):
            data = result.get('data', {})
            print(f"  节点数: {data.get('totalNode', 0)}")
            print(f"  根节点: {data.get('rootIds', [])[:5]}")
        else:
            print(f"  错误: {result.get('error')}")
    except Exception as e:
        print(f"获取失败: {e}")


async def main():
    """主函数"""
    print("浏览器客户端测试")
    print(f"环境变量 BROWSER_MODE: {os.getenv('BROWSER_MODE', '未设置')}")

    # 测试创建
    client = await test_client_creation()

    # 测试连接（可能会失败，这是正常的）
    connected = await test_client_connection(client)

    if connected:
        # 测试基本功能
        await test_navigate(client)
        await test_a11y_tree(client)

    # 关闭客户端
    if client and hasattr(client, 'close'):
        await client.close()

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
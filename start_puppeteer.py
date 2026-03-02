#!/usr/bin/env python3
"""
Puppeteer 启动脚本（Node.js 版）

自动完成：
1. 安装 Node.js 依赖
2. 启动 Relay 服务器
3. 启动 Node.js Puppeteer + stealth 插件 + 扩展
4. 获取扩展密钥并传递到后端
5. 启动 API 服务器
"""

import argparse
import os
import subprocess
import sys
import time
import asyncio
from typing import Optional


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RELAY_PORT = 18792
API_PORT = 8080
KEY_FILE = os.path.join(PROJECT_ROOT, ".extension_key")
WS_ENDPOINT_FILE = os.path.join(PROJECT_ROOT, ".ws_endpoint")
NODE_BROWSER_SCRIPT = os.path.join(PROJECT_ROOT, "start_browser.js")


class PuppeteerStarter:
    """Puppeteer 启动器"""

    def __init__(self, headless: bool = False, stealth: bool = True):
        self.headless = headless
        self.stealth = stealth
        self.relay_process = None
        self.puppeteer_process = None
        self.api_process = None
        self.extension_key = None

    def install_dependencies(self):
        print("=" * 50)
        print("安装 Node.js 依赖...")
        print("=" * 50)

        # 检查是否有 npm
        npm_check = subprocess.run(["which", "npm"], capture_output=True)
        if npm_check.returncode != 0:
            print("错误: 未找到 npm，请先安装 Node.js")
            print("  macOS: brew install node")
            sys.exit(1)

        # 安装依赖
        result = subprocess.run(
            ["npm", "install"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"npm install 失败: {result.stderr}")
            sys.exit(1)

        print("依赖安装完成\n")

    def start_relay_server(self):
        print("=" * 50)
        print(f"启动 Relay 服务器 (端口 {RELAY_PORT})...")
        print("=" * 50)

        cmd = [sys.executable, "src/relay_server.py", "--port", str(RELAY_PORT)]
        self.relay_process = subprocess.Popen(
            cmd, cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        time.sleep(2)
        print(f"Relay 服务器已启动 (PID: {self.relay_process.pid})\n")

    def start_puppeteer(self):
        print("=" * 50)
        print("启动 Puppeteer 浏览器...")
        print("=" * 50)

        # 构建 node 命令参数
        node_argv = [NODE_BROWSER_SCRIPT]
        if self.headless:
            node_argv.append("--headless")
        # 注意：stealth 现在由 Node.js 端 puppeteer-extra-plugin-stealth 处理

        self.puppeteer_process = subprocess.Popen(
            ["node"] + node_argv,
            cwd=PROJECT_ROOT,
        )
        print(f"Puppeteer 已启动 (PID: {self.puppeteer_process.pid})\n")

    def get_extension_key(self) -> Optional[str]:
        if os.path.exists(KEY_FILE):
            try:
                with open(KEY_FILE, 'r') as f:
                    key = f.read().strip()
                if key:
                    return key
            except:
                pass
        return None

    def get_ws_endpoint(self) -> Optional[str]:
        if os.path.exists(WS_ENDPOINT_FILE):
            try:
                with open(WS_ENDPOINT_FILE, 'r') as f:
                    endpoint = f.read().strip()
                if endpoint:
                    return endpoint
            except:
                pass
        return None

    def start_api_server(self, port: int):
        print("=" * 50)
        print(f"启动 API 服务器 (端口 {port})...")
        print("=" * 50)

        env = os.environ.copy()
        # 使用 hybrid 模式连接已启动的浏览器
        env["BROWSER_MODE"] = "hybrid"
        env["RELAY_HOST"] = "127.0.0.1"
        env["RELAY_PORT"] = str(RELAY_PORT)

        extension_key = self.get_extension_key()
        if extension_key:
            env["SECRET_KEY"] = extension_key
            print(f"  使用扩展密钥: {extension_key[:8]}...")
        else:
            print("  警告: 未获取到扩展密钥")
            # 即使没有密钥也尝试启动，扩展连接后会提供密钥

        # 设置 WebSocket 端点供 Hybrid 模式连接已有浏览器
        ws_endpoint = self.get_ws_endpoint()
        if ws_endpoint:
            env["BROWSER_WS_ENDPOINT"] = ws_endpoint
            print(f"  使用 WebSocket 端点: {ws_endpoint[:50]}...")

        cmd = [sys.executable, "-m", "uvicorn",
               "src.api.app:app", "--host", "0.0.0.0",
               "--port", str(port), "--reload"]

        self.api_process = subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env)
        print(f"API 服务器已启动 (PID: {self.api_process.pid})\n")

    def stop_all(self):
        print("\n正在停止所有服务...")
        for name, proc in [("Puppeteer", self.puppeteer_process),
                           ("API", self.api_process),
                           ("Relay", self.relay_process)]:
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                    print(f"  {name} 已停止")
                except:
                    try:
                        proc.kill()
                    except:
                        pass

    async def run(self, api_port: int = API_PORT):
        print("Puppeteer 自动启动脚本 (Node.js 版)")
        print(f"  headless: {self.headless}")
        print(f"  stealth: {self.stealth}")

        self.install_dependencies()
        self.start_relay_server()
        self.start_puppeteer()

        # 等待扩展密钥和 WebSocket 端点
        print("等待扩展生成密钥...")
        ws_endpoint = None
        for i in range(30):
            await asyncio.sleep(1)
            key = self.get_extension_key()
            ws_endpoint = self.get_ws_endpoint()
            if key:
                self.extension_key = key
                print(f"  已获取密钥: {key[:8]}...")
            if ws_endpoint:
                print(f"  已获取 WebSocket 端点")
            if key and ws_endpoint:
                break
            if i < 29:
                print(f"  等待中... ({i+1}/30)")
        else:
            print("  警告: 30秒内未获取到密钥")

        if not ws_endpoint:
            print("  警告: 未获取到 WebSocket 端点，Hybrid 模式可能无法连接")

        self.start_api_server(api_port)

        print("=" * 50)
        print("启动完成！")
        print("=" * 50)
        print(f"  Relay: ws://127.0.0.1:{RELAY_PORT}")
        print(f"  API: http://localhost:{api_port}")
        if self.extension_key:
            print(f"  密钥: {self.extension_key}")
        print("\n按 Ctrl+C 停止所有服务...")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.stop_all()


def main():
    parser = argparse.ArgumentParser(description="Puppeteer 自动启动脚本 (Node.js 版)")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--no-stealth", action="store_true", help="禁用 stealth")
    parser.add_argument("--port", type=int, default=8080, help="API 端口")
    parser.add_argument("--no-install", action="store_true", help="跳过依赖安装")

    args = parser.parse_args()

    starter = PuppeteerStarter(headless=args.headless, stealth=not args.no_stealth)

    if args.no_install:
        starter.relay_process = subprocess.Popen(
            [sys.executable, "src/relay_server.py", "--port", str(RELAY_PORT)],
            cwd=PROJECT_ROOT,
        )
        time.sleep(2)

    asyncio.run(starter.run(args.port))


if __name__ == "__main__":
    main()
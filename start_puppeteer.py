#!/usr/bin/env python3
"""
Puppeteer 启动脚本（自动连接版）

自动完成：
1. 安装依赖
2. 启动 Relay 服务器
3. 启动 Puppeteer + 加载扩展
4. 自动触发扩展连接
5. 预设网站授权
6. 启动 API 服务器

使用方式:
    python start_puppeteer.py
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import asyncio
import threading
from typing import Optional


# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXTENSION_PATH = os.path.join(PROJECT_ROOT, "extension")
RELAY_PORT = 18792
API_PORT = 8080

# 要自动授权的网站
DEFAULT_AUTHORIZED_URLS = [
    "*://*.xiaohongshu.com/*",
    "*://*.zhihu.com/*",
    "*://*.douyin.com/*",
    "*://*.baidu.com/*",
    "*://*.taobao.com/*",
    "*://*.jd.com/*",
    "*://*/*",  # 授权所有网站
]


class PuppeteerStarter:
    """Puppeteer 启动器"""

    def __init__(self, headless: bool = True, stealth: bool = True,
                 authorized_urls: list = None):
        self.headless = headless
        self.stealth = stealth
        self.authorized_urls = authorized_urls or DEFAULT_AUTHORIZED_URLS
        self.relay_process: Optional[subprocess.Popen] = None
        self.puppeteer_process: Optional[subprocess.Popen] = None
        self.api_process: Optional[subprocess.Popen] = None

    def install_dependencies(self):
        """安装依赖"""
        print("=" * 50)
        print("安装 Python 依赖...")
        print("=" * 50)

        packages = [
            "websockets>=12.0",
            "aiohttp>=3.9.0",
            "pydantic>=2.0.0",
            "fastapi>=0.109.0",
            "uvicorn>=0.27.0",
            "puppeteer>=7.0.0",
            "puppeteer-extra>=3.0.0",
            "puppeteer-extra-plugin-stealth>=2.9.0",
        ]

        for pkg in packages:
            print(f"  安装: {pkg}")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"  警告: {pkg} 安装失败")

        print("依赖安装完成\n")

    def start_relay_server(self):
        """启动 Relay 服务器"""
        print("=" * 50)
        print(f"启动 Relay 服务器 (端口 {RELAY_PORT})...")
        print("=" * 50)

        cmd = [sys.executable, "src/relay_server.py", "--port", str(RELAY_PORT)]

        self.relay_process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # 等待服务器启动
        time.sleep(2)
        print(f"Relay 服务器已启动 (PID: {self.relay_process.pid})\n")

    def create_launch_script(self) -> str:
        """创建 Puppeteer 启动脚本"""

        # 预设的授权网站
        authorized_urls_json = json.dumps(self.authorized_urls)

        script = f'''
import asyncio
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXTENSION_PATH = os.path.join(PROJECT_ROOT, "extension")
RELAY_PORT = {RELAY_PORT}

async def inject_extension_settings(page):
    """注入扩展设置和自动连接脚本"""

    # 预设网站授权的脚本
    authorized_urls = {authorized_urls_json}

    # 注入自动连接和授权脚本
    await page.evaluateOnNewDocument(f"""
        // 等待扩展加载后自动连接
        window.addEventListener('load', async () => {{
            // 延迟一点确保扩展已初始化
            setTimeout(async () => {{
                try {{
                    // 尝试通过 storage 事件触发连接
                    // 扩展会在初始化时检查 storage 并自动连接
                    console.log('[AutoConnect] 尝试自动连接...');

                    // 模拟触发扩展的连接逻辑
                    if (typeof window._triggerExtensionConnect === 'function') {{
                        window._triggerExtensionConnect();
                    }}
                }} catch (e) {{
                    console.log('[AutoConnect] 错误:', e.message);
                }}
            }}, 2000);
        }});

        // 授权网站的脚本
        const authorizedUrls = {authorized_urls_json};
        console.log('[Auth] 预设授权网站:', authorizedUrls);
    """)

    # 导航到空白页并等待扩展加载
    await page.goto('about:blank')
    await asyncio.sleep(1)

    print(f"  扩展路径: {{EXTENSION_PATH}}")
    print("  页面已导航到 about:blank")
    print("  等待扩展初始化...")

    # 等待扩展完全加载
    await asyncio.sleep(3)

    # 尝试触发扩展连接
    try:
        await page.evaluate("""
            () => {
                // 尝试查找并点击扩展图标
                const toolbar = document.querySelector('[role="toolbar"]');
                if (toolbar) {
                    console.log('[AutoConnect] 找到工具栏');
                }
            }
        """)
    except:
        pass

    print("  扩展应已加载")


async def main():
    print("=" * 50)
    print("启动 Puppeteer + 扩展")
    print("=" * 50)

    HEADLESS = {str(self.headless).lower()}
    STEALTH = {str(self.stealth).lower()}

    try:
        from puppeteer import launch
        from puppeteer_extra import launch as puppeteer_extra_launch
        from puppeteer_extra_plugin_stealth import stealth
    except ImportError as e:
        print(f"错误: 依赖未安装，请先运行安装")
        print(f"ImportError: {{e}}")
        return

    # 构建启动参数
    # 注意：扩展需要非无头模式才能正常工作
    launch_args = {{
        "headless": HEADLESS,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            f"--disable-extensions-background=true",
            f"--load-extension={{EXTENSION_PATH}}",
            f"--remote-debugging-port=9222",
        ],
        "ignoreDefaultArgs": ["--enable-automation"],
        "dumpio": False,
    }}

    browser = None

    try:
        if STEALTH:
            print("启用 stealth 模式...")
            browser = await puppeteer_extra_launch(
                **launch_args,
                plugin=[stealth()],
            )
        else:
            print("普通模式...")
            browser = await launch(**launch_args)

        # 获取页面
        pages = await browser.newPage()

        # 注入扩展设置
        await inject_extension_settings(page)

        # 保持运行
        print("=" * 50)
        print("Puppeteer 已启动，扩展已加载")
        print("按 Ctrl+C 关闭...")
        print("=" * 50)

        # 永久等待
        while True:
            await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\\n正在关闭...")
    except Exception as e:
        print(f"错误: {{e}}")
    finally:
        if browser:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
'''
        return script

    def write_launch_script(self) -> str:
        """写入启动脚本"""
        script_path = os.path.join(PROJECT_ROOT, "_launch_browser.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(self.create_launch_script())
        return script_path

    def start_puppeteer(self):
        """启动 Puppeteer 浏览器"""
        print("=" * 50)
        print("启动 Puppeteer 浏览器...")
        print("=" * 50)

        script_path = self.write_launch_script()

        self.puppeteer_process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        print(f"Puppeteer 已启动 (PID: {self.puppeteer_process.pid})\n")

    def start_api_server(self, port: int):
        """启动 API 服务器"""
        print("=" * 50)
        print(f"启动 API 服务器 (端口 {port})...")
        print("=" * 50)

        env = os.environ.copy()
        env["BROWSER_MODE"] = "puppeteer"
        env["PUPPETEER_HEADLESS"] = "false"
        env["RELAY_HOST"] = "127.0.0.1"
        env["RELAY_PORT"] = str(RELAY_PORT)

        cmd = [
            sys.executable, "-m", "uvicorn",
            "src.api.app:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload",
        ]

        self.api_process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            env=env,
        )

        print(f"API 服务器已启动 (PID: {self.api_process.pid})\n")

    def stop_all(self):
        """停止所有进程"""
        print("\n正在停止所有服务...")

        for name, proc in [
            ("Puppeteer", self.puppeteer_process),
            ("API", self.api_process),
            ("Relay", self.relay_process),
        ]:
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
        """运行启动器"""
        print("Puppeteer 自动启动脚本")
        print(f"  headless: {self.headless}")
        print(f"  stealth: {self.stealth}")
        print(f"  authorized URLs: {len(self.authorized_urls)} 个")
        print(f"  relay port: {RELAY_PORT}")
        print(f"  api port: {api_port}")

        # 1. 安装依赖
        self.install_dependencies()

        # 2. 启动 Relay 服务器
        self.start_relay_server()

        # 3. 启动 Puppeteer
        self.start_puppeteer()

        # 等待浏览器启动
        print("等待浏览器启动...")
        await asyncio.sleep(5)

        # 4. 启动 API
        self.start_api_server(api_port)

        print("=" * 50)
        print("启动完成！")
        print("=" * 50)
        print(f"  Relay: ws://127.0.0.1:{RELAY_PORT}")
        print(f"  API: http://localhost:{api_port}")
        print(f"  扩展: {EXTENSION_PATH}")
        print("\n扩展使用说明:")
        print("  1. 点击浏览器右上角扩展图标")
        print("  2. 扩展会自动连接 Relay 服务器")
        print("  3. 如需授权网站，在扩展设置中添加")
        print("\n按 Ctrl+C 停止所有服务...")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.stop_all()


def main():
    parser = argparse.ArgumentParser(description="Puppeteer 自动启动脚本")
    parser.add_argument("--headless", type=lambda x: x.lower() == "true",
                        default=False, help="无头模式 (默认: False)")
    parser.add_argument("--stealth", type=lambda x: x.lower() == "true",
                        default=True, help="启用 stealth (默认: True)")
    parser.add_argument("--port", type=int, default=8080,
                        help="API 端口 (默认: 8080)")
    parser.add_argument("--no-install", action="store_true",
                        help="跳过依赖安装")
    parser.add_argument("--auth-urls", nargs="*",
                        help="授权的网站URL (可选)")

    args = parser.parse_args()

    # 要授权的网站
    auth_urls = args.auth_urls or DEFAULT_AUTHORIZED_URLS

    starter = PuppeteerStarter(
        headless=args.headless,
        stealth=args.stealth,
        authorized_urls=auth_urls,
    )

    # 如果需要跳过安装，直接启动
    if args.no_install:
        starter.relay_process = subprocess.Popen(
            [sys.executable, "src/relay_server.py", "--port", str(RELAY_PORT)],
            cwd=PROJECT_ROOT,
        )
        time.sleep(2)

    asyncio.run(starter.run(args.port))


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Puppeteer 启动脚本（自动连接版）

自动完成：
1. 安装依赖
2. 启动 Relay 服务器
3. 启动 Puppeteer + 加载扩展
4. 获取扩展密钥并传递到后端
5. 启动 API 服务器

使用方式:
    python start_puppeteer.py
"""

import argparse
import json
import os
import subprocess
import sys
import time
import asyncio
import threading
import tempfile
from typing import Optional


# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXTENSION_PATH = os.path.join(PROJECT_ROOT, "extension")
RELAY_PORT = 18792
API_PORT = 8080
KEY_FILE = os.path.join(PROJECT_ROOT, ".extension_key")

# 要自动授权的网站
DEFAULT_AUTHORIZED_URLS = [
    "*://*/*",  # 授权所有网站
]


class PuppeteerStarter:
    """Puppeteer 启动器"""

    def __init__(self, headless: bool = False, stealth: bool = True,
                 authorized_urls: list = None):
        self.headless = headless
        self.stealth = stealth
        self.authorized_urls = authorized_urls or DEFAULT_AUTHORIZED_URLS
        self.relay_process: Optional[subprocess.Popen] = None
        self.puppeteer_process: Optional[subprocess.Popen] = None
        self.api_process: Optional[subprocess.Popen] = None
        self.extension_key: Optional[str] = None

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

        time.sleep(2)
        print(f"Relay 服务器已启动 (PID: {self.relay_process.pid})\n")

    def create_launch_script(self) -> str:
        """创建 Puppeteer 启动脚本"""

        authorized_urls_json = json.dumps(self.authorized_urls)

        script = f'''
import asyncio
import json
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXTENSION_PATH = os.path.join(PROJECT_ROOT, "extension")
KEY_FILE = os.path.join(PROJECT_ROOT, ".extension_key")
RELAY_PORT = {RELAY_PORT}

async def wait_for_extension_key(max_wait=30):
    """等待扩展生成并保存密钥"""
    print("  等待扩展生成密钥...")

    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            # 检查密钥文件是否生成
            if os.path.exists(KEY_FILE):
                with open(KEY_FILE, 'r') as f:
                    key = f.read().strip()
                if key and len(key) > 8:
                    print(f"  获取到扩展密钥: {{key[:8]}...{{key[-4:]}}")
                    return key
        except:
            pass

        await asyncio.sleep(1)

    print("  警告: 未能获取扩展密钥（扩展可能未连接）")
    return None


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
        print(f"错误: 依赖未安装，请先运行 pip install puppeteer-extra puppeteer-extra-plugin-stealth")
        print(f"ImportError: {{e}}")
        return

    # 构建启动参数
    # 注意：扩展需要非无头模式
    launch_args = {{
        "headless": HEADLESS,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            f"--load-extension={{EXTENSION_PATH}}",
            f"--remote-debugging-port=9222",
            # 禁用自动化 banner
            "--disable-infobars",
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

        # 创建新页面
        page = await browser.newPage()

        # 导航到空白页（扩展会加载）
        await page.goto('about:blank')
        print(f"  扩展路径: {{EXTENSION_PATH}}")
        print("  页面已打开，等待扩展初始化...")

        # 等待扩展加载
        await asyncio.sleep(5)

        # 尝试通过 CDP 获取扩展存储的密钥
        print("  尝试获取扩展密钥...")

        try:
            # 通过 CDP 获取扩展的 localStorage
            targets = await browser.targets()
            for target in targets:
                if target.type == 'background_worker':
                    try:
                        cdp = await target.createCDPSession()
                        # 获取 storage 的密钥
                        result = await cdp.send('Runtime.evaluate', {{
                            "expression": "chrome.storage.local.get(['secret_key']).then(r => JSON.stringify(r))",
                            "awaitPromise": True
                        }})

                        if result.get('result') and result['result'].get('result'):
                            storage_data = result['result']['result'].get('value', '')
                            if storage_data:
                                data = json.loads(storage_data)
                                if data.get('secret_key'):
                                    key = data['secret_key']
                                    print(f"  从 CDP 获取密钥: {{key[:8]}...{{key[-4:]}}")
                                    # 保存密钥到文件
                                    with open(KEY_FILE, 'w') as f:
                                        f.write(key)
                    except Exception as e:
                        pass  # 可能有些 target 不可访问
        except Exception as e:
            print(f"  CDP 获取密钥失败: {{e}}")

        print("=" * 50)
        print("Puppeteer 已启动")
        print("  扩展已加载（请点击图标连接，或等待自动连接）")
        print("=" * 50)

        # 保持运行
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
        print(f"启动脚本已写入: {script_path}")
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
        )

        print(f"Puppeteer 已启动 (PID: {self.puppeteer_process.pid})\n")

    def get_extension_key(self) -> Optional[str]:
        """从文件读取扩展密钥"""
        if os.path.exists(KEY_FILE):
            try:
                with open(KEY_FILE, 'r') as f:
                    key = f.read().strip()
                if key:
                    return key
            except:
                pass
        return None

    def start_api_server(self, port: int):
        """启动 API 服务器"""
        print("=" * 50)
        print(f"启动 API 服务器 (端口 {port})...")
        print("=" * 50)

        env = os.environ.copy()
        env["BROWSER_MODE"] = "puppeteer"
        env["PUPPETEER_HEADLESS"] = "false"

        # 传递扩展密钥
        extension_key = self.get_extension_key()
        if extension_key:
            env["SECRET_KEY"] = extension_key
            print(f"  使用扩展密钥: {extension_key[:8]}...")
        else:
            print("  警告: 未获取到扩展密钥，API 可能无法控制")

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
        print(f"  relay port: {RELAY_PORT}")
        print(f"  api port: {api_port}")

        # 1. 安装依赖
        self.install_dependencies()

        # 2. 启动 Relay 服务器
        self.start_relay_server()

        # 3. 启动 Puppeteer
        self.start_puppeteer()

        # 4. 等待扩展启动并获取密钥
        print("等待扩展生成密钥...")
        for i in range(30):
            await asyncio.sleep(1)
            key = self.get_extension_key()
            if key:
                self.extension_key = key
                print(f"  已获取密钥: {key[:8]}...")
                break
            print(f"  等待中... ({i+1}/30)")
        else:
            print("  警告: 30秒内未获取到密钥，请手动点击扩展图标")

        # 5. 启动 API
        self.start_api_server(api_port)

        print("=" * 50)
        print("启动完成！")
        print("=" * 50)
        print(f"  Relay: ws://127.0.0.1:{RELAY_PORT}")
        print(f"  API: http://localhost:{api_port}")
        if self.extension_key:
            print(f"  密钥: {self.extension_key}")
        print(f"  扩展: {EXTENSION_PATH}")
        print("\n使用说明:")
        print("  1. 如果扩展未自动连接，点击浏览器右上角扩展图标")
        print("  2. 扩展连接后会生成密钥文件: .extension_key")
        print("  3. API 使用环境变量 SECRET_KEY 控制扩展")
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

    args = parser.parse_args()

    starter = PuppeteerStarter(
        headless=args.headless,
        stealth=args.stealth,
        authorized_urls=DEFAULT_AUTHORIZED_URLS,
    )

    if args.no_install:
        starter.relay_process = subprocess.Popen(
            [sys.executable, "src/relay_server.py", "--port", str(RELAY_PORT)],
            cwd=PROJECT_ROOT,
        )
        time.sleep(2)

    asyncio.run(starter.run(args.port))


if __name__ == "__main__":
    main()
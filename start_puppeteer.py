#!/usr/bin/env python3
"""
Puppeteer 启动脚本（自动连接版）

自动完成：
1. 安装依赖
2. 启动 Relay 服务器
3. 启动 Puppeteer + 加载扩展
4. 获取扩展密钥并传递到后端
5. 启动 API 服务器
"""

import argparse
import json
import os
import subprocess
import sys
import time
import asyncio
from typing import Optional


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXTENSION_PATH = os.path.join(PROJECT_ROOT, "extension")
RELAY_PORT = 18792
API_PORT = 8080
KEY_FILE = os.path.join(PROJECT_ROOT, ".extension_key")

DEFAULT_AUTHORIZED_URLS = ["*://*/*"]


def get_launch_script_template(python_path: str):
    """获取 Puppeteer 启动脚本模板"""
    # 使用普通字符串避免 f-string 嵌套问题
    template = '''#!/usr/bin/env python3
"""
Puppeteer 启动脚本 - 由主脚本生成
"""
import asyncio
import json
import os
import sys
import time

# 使用虚拟环境的 Python
sys.path.insert(0, r"{{VENV_PATH}}/lib/python3.10/site-packages")

PROJECT_ROOT = r"{{PROJECT_ROOT}}"
EXTENSION_PATH = r"{{EXTENSION_PATH}}"
KEY_FILE = r"{{KEY_FILE}}"
RELAY_PORT = {{RELAY_PORT}}

async def main():
    headless = {{HEADLESS}}
    stealth = {{STEALTH}}

    try:
        from puppeteer import launch
        from puppeteer_extra import launch as puppeteer_extra_launch
        from puppeteer_extra_plugin_stealth import stealth
    except ImportError as e:
        print("错误: 依赖未安装: " + str(e))
        return

    ext_path = EXTENSION_PATH
    launch_args = {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--load-extension=" + ext_path,
            "--remote-debugging-port=9222",
            "--disable-infobars",
        ],
        "ignoreDefaultArgs": ["--enable-automation"],
        "dumpio": False,
    }

    browser = None
    try:
        if stealth:
            print("启用 stealth 模式...")
            browser = await puppeteer_extra_launch(**launch_args, plugin=[stealth()])
        else:
            print("普通模式...")
            browser = await launch(**launch_args)

        page = await browser.newPage()
        await page.goto('about:blank')

        print("  扩展路径: " + EXTENSION_PATH)
        print("  页面已打开")

        # 尝试获取扩展密钥
        await asyncio.sleep(3)
        print("  尝试获取扩展密钥...")

        try:
            targets = await browser.targets()
            for target in targets:
                if target.type == 'background_worker':
                    try:
                        cdp = await target.createCDPSession()
                        result = await cdp.send('Runtime.evaluate', {
                            "expression": "chrome.storage.local.get(['secret_key']).then(r => JSON.stringify(r))",
                            "awaitPromise": True
                        })
                        if result.get('result') and result['result'].get('result'):
                            storage_data = result['result']['result'].get('value', '')
                            if storage_data:
                                data = json.loads(storage_data)
                                if data.get('secret_key'):
                                    key = data['secret_key']
                                    print("  获取到密钥: " + key[:8] + "..." + key[-4:])
                                    with open(KEY_FILE, 'w') as f:
                                        f.write(key)
                    except:
                        pass
        except:
            pass

        print("=" * 50)
        print("Puppeteer 已启动")
        print("  扩展已加载")
        print("=" * 50)

        while True:
            await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\\n正在关闭...")
    except Exception as e:
        print("错误: " + str(e))
    finally:
        if browser:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
'''
    return template.replace("{{VENV_PATH}}", python_path)


def write_launch_script(headless: bool, stealth: bool) -> str:
    """写入启动脚本"""
    script_path = os.path.join(PROJECT_ROOT, "_launch_browser.py")

    # 获取虚拟环境的 site-packages 路径
    venv_path = os.path.dirname(os.path.dirname(sys.executable))

    template = get_launch_script_template(venv_path)
    content = template.replace("{{PROJECT_ROOT}}", PROJECT_ROOT) \
                      .replace("{{EXTENSION_PATH}}", EXTENSION_PATH) \
                      .replace("{{KEY_FILE}}", KEY_FILE) \
                      .replace("{{RELAY_PORT}}", str(RELAY_PORT)) \
                      .replace("{{HEADLESS}}", str(headless)) \
                      .replace("{{STEALTH}}", str(stealth))

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)

    return script_path


class PuppeteerStarter:
    """Puppeteer 启动器"""

    def __init__(self, headless: bool = False, stealth: bool = True,
                 authorized_urls: list = None):
        self.headless = headless
        self.stealth = stealth
        self.authorized_urls = authorized_urls or DEFAULT_AUTHORIZED_URLS
        self.relay_process = None
        self.puppeteer_process = None
        self.api_process = None
        self.extension_key = None

    def install_dependencies(self):
        print("=" * 50)
        print("安装 Python 依赖...")
        print("=" * 50)

        packages = [
            "websockets>=12.0", "aiohttp>=3.9.0", "pydantic>=2.0.0",
            "fastapi>=0.109.0", "uvicorn>=0.27.0",
            "puppeteer>=7.0.0", "puppeteer-extra>=3.0.0",
            "puppeteer-extra-plugin-stealth>=2.9.0",
        ]

        for pkg in packages:
            print(f"  安装: {pkg}")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                capture_output=True, text=True
            )

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

        script_path = write_launch_script(self.headless, self.stealth)
        print(f"启动脚本已写入: {script_path}")

        self.puppeteer_process = subprocess.Popen(
            [sys.executable, script_path],
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

    def start_api_server(self, port: int):
        print("=" * 50)
        print(f"启动 API 服务器 (端口 {port})...")
        print("=" * 50)

        env = os.environ.copy()
        env["BROWSER_MODE"] = "puppeteer"
        env["PUPPETEER_HEADLESS"] = "false"

        extension_key = self.get_extension_key()
        if extension_key:
            env["SECRET_KEY"] = extension_key
            print(f"  使用扩展密钥: {extension_key[:8]}...")
        else:
            print("  警告: 未获取到扩展密钥")

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
        print("Puppeteer 自动启动脚本")
        print(f"  headless: {self.headless}")
        print(f"  stealth: {self.stealth}")

        self.install_dependencies()
        self.start_relay_server()
        self.start_puppeteer()

        # 等待扩展密钥
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
            print("  警告: 30秒内未获取到密钥")

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
    parser = argparse.ArgumentParser(description="Puppeteer 自动启动脚本")
    parser.add_argument("--headless", type=lambda x: x.lower() == "true",
                        default=False, help="无头模式")
    parser.add_argument("--stealth", type=lambda x: x.lower() == "true",
                        default=True, help="启用 stealth")
    parser.add_argument("--port", type=int, default=8080, help="API 端口")
    parser.add_argument("--no-install", action="store_true", help="跳过依赖安装")

    args = parser.parse_args()

    starter = PuppeteerStarter(headless=args.headless, stealth=args.stealth)

    if args.no_install:
        starter.relay_process = subprocess.Popen(
            [sys.executable, "src/relay_server.py", "--port", str(RELAY_PORT)],
            cwd=PROJECT_ROOT,
        )
        time.sleep(2)

    asyncio.run(starter.run(args.port))


if __name__ == "__main__":
    main()
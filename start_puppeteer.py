#!/usr/bin/env python3
"""
Puppeteer 启动脚本

自动安装依赖并启动加载了项目扩展的 Puppeteer 浏览器。

使用方式:
    python start_puppeteer.py

参数:
    --headless    无头模式运行（默认 True）
    --stealth    启用 stealth 模式（默认 True）
    --port       API 服务器端口（默认 8080）
    --no-install  跳过依赖安装

示例:
    python start_puppeteer.py --headless=false --port=8080
"""

import argparse
import os
import subprocess
import sys
import asyncio


# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXTENSION_PATH = os.path.join(PROJECT_ROOT, "extension")
REQUIREMENTS = [
    "websockets>=12.0",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "puppeteer>=7.0.0",
    "puppeteer-extra>=3.0.0",
    "puppeteer-extra-plugin-stealth>=2.9.0",
]


def install_dependencies():
    """安装 Python 依赖"""
    print("=" * 50)
    print("安装 Python 依赖...")
    print("=" * 50)

    for pkg in REQUIREMENTS:
        print(f"  安装: {pkg}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg, "-q"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"  警告: {pkg} 安装失败 - {result.stderr}")

    print("依赖安装完成")


def create_puppeteer_script(headless: bool, stealth: bool) -> str:
    """生成 Puppeteer 启动脚本内容"""

    return f'''
import asyncio
import os
import sys

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXTENSION_PATH = os.path.join(PROJECT_ROOT, "extension")

# 启动参数
HEADLESS = {str(headless).lower()}
STEALTH = {str(stealth).lower()}

async def main():
    print("=" * 50)
    print(f"启动 Puppeteer (headless={{HEADLESS}}, stealth={{STEALTH}})")
    print("=" * 50)
    print(f"扩展路径: {{EXTENSION_PATH}}")

    try:
        from puppeteer import launch
        from puppeteer_extra import launch as puppeteer_extra_launch
        from puppeteer_extra_plugin_stealth import stealth
    except ImportError as e:
        print(f"错误: 请先安装依赖 pip install puppeteer-extra puppeteer-extra-plugin-stealth")
        print(f"ImportError: {{e}}")
        return

    # 构建启动参数
    launch_args = {{
        "headless": HEADLESS,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            f"--disable-extensions-background={not HEADLESS}",
            # 加载扩展
            f"--disable-extensions-background=true",
            f"--load-extension={{EXTENSION_PATH}}",
        ],
        "ignoreDefaultArgs": ["--enable-automation"],
    }}

    browser = None
    page = None

    try:
        if STEALTH:
            # 使用 stealth 插件
            print("启用 stealth 模式...")
            browser = await puppeteer_extra_launch(
                **launch_args,
                plugins=[stealth()],
            )
        else:
            # 普通模式
            print("普通模式（无 stealth）...")
            browser = await launch(**launch_args)

        # 获取页面
        pages = await browser.pagesArray()
        if pages:
            page = pages[0]
        else:
            page = await browser.newPage()

        print(f"浏览器已启动: {{page.url}}")
        print("扩展已加载")

        # 保持浏览器运行
        print("按 Ctrl+C 关闭浏览器...")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\\n正在关闭浏览器...")
    except Exception as e:
        print(f"错误: {{e}}")
    finally:
        if browser:
            await browser.close()
            print("浏览器已关闭")


if __name__ == "__main__":
    asyncio.run(main())
'''


def write_puppeteer_script(content: str):
    """写入 Puppeteer 启动脚本"""
    script_path = os.path.join(PROJECT_ROOT, "_run_puppeteer.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"脚本已写入: {script_path}")
    return script_path


def start_api_server(port: int):
    """启动 API 服务器"""
    print("=" * 50)
    print(f"启动 API 服务器 (端口 {port})...")
    print("=" * 50)

    # 设置环境变量
    env = os.environ.copy()
    env["BROWSER_MODE"] = "puppeteer"
    env["PUPPETEER_HEADLESS"] = "false"  # 启动有头浏览器让扩展可以连接

    # 启动 uvicorn
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.api.app:app",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--reload",
    ]

    print(f"执行: {' '.join(cmd)}")
    print(f"环境变量: BROWSER_MODE=puppeteer")

    # 切换到项目目录
    proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
    )

    return proc


async def main():
    parser = argparse.ArgumentParser(description="Puppeteer 启动脚本")
    parser.add_argument("--headless", type=lambda x: x.lower() == "true",
                        default=True, help="无头模式运行 (default: True)")
    parser.add_argument("--stealth", type=lambda x: x.lower() == "true",
                        default=True, help="启用 stealth 模式 (default: True)")
    parser.add_argument("--port", type=int, default=8080,
                        help="API 服务器端口 (default: 8080)")
    parser.add_argument("--no-install", action="store_true",
                        help="跳过依赖安装")

    args = parser.parse_args()

    print("Puppeteer 启动脚本")
    print(f"  headless: {args.headless}")
    print(f"  stealth: {args.stealth}")
    print(f"  port: {args.port}")
    print(f"  extension: {EXTENSION_PATH}")

    # 检查扩展是否存在
    if not os.path.exists(EXTENSION_PATH):
        print(f"错误: 扩展目录不存在: {EXTENSION_PATH}")
        return

    manifest = os.path.join(EXTENSION_PATH, "manifest.json")
    if not os.path.exists(manifest):
        print(f"错误: manifest.json 不存在: {manifest}")
        return

    # 安装依赖
    if not args.no_install:
        install_dependencies()

    # 生成 Puppeteer 脚本
    script_content = create_puppeteer_script(args.headless, args.stealth)
    script_path = write_puppeteer_script(script_content)

    print("\n" + "=" * 50)
    print("启动 Puppeteer 浏览器...")
    print("=" * 50)

    # 启动 Puppeteer 浏览器（在后台运行）
    browser_proc = subprocess.Popen(
        [sys.executable, script_path],
        cwd=PROJECT_ROOT,
    )

    print(f"Puppeteer 进程 PID: {browser_proc.pid}")

    # 等待浏览器启动
    await asyncio.sleep(3)

    # 启动 API 服务器
    api_proc = start_api_server(args.port)

    print("\n" + "=" * 50)
    print("启动完成！")
    print("=" * 50)
    print(f"  Puppeteer: PID {browser_proc.pid}")
    print(f"  API: http://localhost:{args.port}")
    print(f"  扩展: {EXTENSION_PATH}")
    print("\n按 Ctrl+C 停止所有服务...")

    try:
        # 等待用户中断
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务...")

    # 清理
    browser_proc.terminate()
    api_proc.terminate()
    print("已停止所有服务")


if __name__ == "__main__":
    asyncio.run(main())
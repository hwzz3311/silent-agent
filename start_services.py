#!/usr/bin/env python3
"""
Neurone 服务启动脚本

启动 Neurone 的所有服务：
1. WebSocket Relay 服务器 (:18792) - Chrome 扩展通信
2. REST API 服务 (:8080) - HTTP API 接口

使用方式:
    python start_services.py              # 启动所有服务
    python start_services.py relay        # 只启动 Relay
    python start_services.py api          # 只启动 API
    python start_services.py --help       # 显示帮助
"""

import asyncio
import argparse
import logging
import signal
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger("Neurone")

# 颜色输出
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_status(msg: str):
    print(f"{BLUE}[Neurone]{RESET} {msg}")


class NeuroneLauncher:
    """Neurone 服务启动器"""

    def __init__(
        self,
        relay_port: int = 18792,
        api_port: int = 8080,
        api_host: str = "0.0.0.0",
        relay_host: str = "127.0.0.1",
        log_level: str = "INFO",
    ):
        self.relay_port = relay_port
        self.api_port = api_port
        self.api_host = api_host
        self.relay_host = relay_host
        self.log_level = log_level

        self.relay_process = None
        self.api_process = None
        self._shutdown = False

    def start_relay(self):
        """启动 Relay 服务器 (WebSocket)"""
        print_status(f"启动 WebSocket Relay 服务器 on {self.relay_host}:{self.relay_port}...")

        try:
            from src.relay_server import NeuroneRelayServer

            server = NeuroneRelayServer(host=self.relay_host, port=self.relay_port)
            return server
        except ImportError as e:
            logger.error(f"无法导入 Relay Server: {e}")
            # 尝试使用 subprocess 启动
            return self._start_relay_subprocess()

    def _start_relay_subprocess(self):
        """使用子进程启动 Relay"""
        cmd = [
            sys.executable,
            "-c",
            f"""
import asyncio
from src.relay_server import NeuroneRelayServer
asyncio.run(NeuroneRelayServer(port={self.relay_port}).run())
"""
        ]
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    async def run_relay_async(self):
        """异步运行 Relay 服务器"""
        try:
            from src.relay_server import NeuroneRelayServer

            server = NeuroneRelayServer(host=self.relay_host, port=self.relay_port)
            await server.run()
        except ImportError as e:
            print_status(f"错误: 无法导入 Relay Server - {e}")
            print_status("请确保已安装所需依赖: pip install websockets")
            sys.exit(1)

    def start_api(self):
        """启动 REST API 服务"""
        print_status(f"启动 REST API 服务 on {self.api_host}:{self.api_port}...")

        try:
            from src.api.app import app
            import uvicorn

            config = uvicorn.Config(
                app,
                host=self.api_host,
                port=self.api_port,
                log_level=self.log_level.lower(),
            )
            server = uvicorn.Server(config=config)
            return server
        except ImportError as e:
            logger.error(f"无法导入 API Server: {e}")
            print_status(f"错误: {e}")
            sys.exit(1)

    async def start_all(self):
        """启动所有服务"""
        print_status("=" * 50)
        print_status("  Neurone 服务启动器")
        print_status("=" * 50)
        print_status("")

        # 设置信号处理
        loop = asyncio.get_event_loop()

        async def shutdown(sig):
            print_status(f"\n收到信号 {sig}，正在关闭...")
            self._shutdown = True

        for s in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(s, lambda: asyncio.create_task(shutdown(s)))

        # 并发启动两个服务
        import uvicorn

        # Relay 服务器
        try:
            from src.relay_server import NeuroneRelayServer
            relay_server = NeuroneRelayServer(
                host=self.relay_host,
                port=self.relay_port,
            )
            relay_task = asyncio.create_task(relay_server.run())
        except ImportError as e:
            print_status(f"错误: 无法启动 Relay Server - {e}")
            print_status("请检查是否安装了 websockets 库")
            sys.exit(1)

        # API 服务器
        try:
            from src.api.app import app
            api_config = uvicorn.Config(
                app,
                host=self.api_host,
                port=self.api_port,
                log_level=self.log_level.lower(),
            )
            api_server = uvicorn.Server(api_config)
            api_task = asyncio.create_task(api_server.serve())
        except ImportError as e:
            print_status(f"错误: 无法启动 API Server - {e}")
            print_status("请检查是否安装了 fastapi 和 uvicorn")
            sys.exit(1)

        print_status("服务状态:")
        print_status(f"  - WebSocket Relay: ws://{self.relay_host}:{self.relay_port}")
        print_status(f"    - 扩展连接: ws://{self.relay_host}:{self.relay_port}/extension")
        print_status(f"    - 控制器连接: ws://{self.relay_host}:{self.relay_port}/controller")
        print_status(f"    - 健康检查: http://{self.relay_host}:{self.relay_port}/health")
        print_status(f"  - REST API: http://{self.api_host}:{self.api_port}")
        print_status(f"    - API 文档: http://{self.api_host}:{self.api_port}/docs")
        print_status(f"    - 健康检查: http://{self.api_host}:{self.api_port}/health")
        print_status("")
        print_status("按 Ctrl+C 停止所有服务")
        print_status("")

        # 等待服务或信号
        try:
            await asyncio.gather(relay_task, api_task)
        except asyncio.CancelledError:
            print_status("正在关闭服务...")
            relay_task.cancel()
            api_task.cancel()
            await asyncio.gather(relay_task, api_task, return_exceptions=True)

        print_status("所有服务已关闭")

    def start_relay_only(self):
        """只启动 Relay 服务器"""
        asyncio.run(self.run_relay_async())

    def start_api_only(self):
        """只启动 API 服务"""
        import uvicorn
        from src.api.app import app

        config = uvicorn.Config(
            app,
            host=self.api_host,
            port=self.api_port,
            log_level=self.log_level.lower(),
        )
        server = uvicorn.Server(config=config)
        asyncio.run(server.serve())


def main():
    parser = argparse.ArgumentParser(
        description="Neurone 服务启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python start_services.py              # 启动所有服务
    python start_services.py relay        # 只启动 Relay (WebSocket)
    python start_services.py api          # 只启动 API (HTTP)
    python start_services.py --relay-port 9999    # 自定义 Relay 端口
    python start_services.py --api-port 3000     # 自定义 API 端口
    python start_services.py --log-level DEBUG   # 调试模式
        """,
    )

    parser.add_argument(
        "--relay-port",
        type=int,
        default=18792,
        help="Relay 服务器端口 (默认: 18792)",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=8080,
        help="API 服务器端口 (默认: 8080)",
    )
    parser.add_argument(
        "--relay-host",
        type=str,
        default="127.0.0.1",
        help="Relay 服务器地址 (默认: 127.0.0.1)",
    )
    parser.add_argument(
        "--api-host",
        type=str,
        default="0.0.0.0",
        help="API 服务器地址 (默认: 0.0.0.0)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )

    # 位置参数
    parser.add_argument(
        "command",
        choices=["all", "relay", "api"],
        nargs="?",
        default="all",
        help="启动命令 (默认: all)",
    )

    args = parser.parse_args()

    # 创建启动器
    launcher = NeuroneLauncher(
        relay_port=args.relay_port,
        api_port=args.api_port,
        relay_host=args.relay_host,
        api_host=args.api_host,
        log_level=args.log_level,
    )

    # 根据命令启动
    if args.command == "relay":
        launcher.start_relay_only()
    elif args.command == "api":
        launcher.start_api_only()
    else:
        asyncio.run(launcher.start_all())


if __name__ == "__main__":
    main()
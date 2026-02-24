#!/usr/bin/env python3
"""
Neurone Native Messaging Host

作为 Chrome 扩展与 CDP 之间的桥梁:
- 从 stdin 接收 Native Messaging 消息（4字节长度前缀 + JSON）
- 解析命令类型
- 调用 CDP Client 执行操作
- 将结果写入 stdout

消息格式:
{
    "type": "command",
    "action": "get_dom" | "click" | "type" | "scroll",
    "params": {...}
}

响应格式:
{
    "success": true,
    "result": {...}
}
"""

import asyncio
import json
import sys
import os
from typing import Optional, Dict, Any

# Add python directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cdp_client import CDPClient


class NeuroneHost:
    """Native Messaging Host 处理器"""

    SUPPORTED_ACTIONS = {
        "get_dom": "获取页面 DOM 树",
        "click": "在指定坐标点击",
        "type": "输入文本",
        "scroll": "滚动页面",
        "health": "健康检查",
    }

    def __init__(self):
        self.cdp_client: Optional[CDPClient] = None

    async def handle_command(self, command: dict) -> dict:
        """处理单个命令"""
        action = command.get("action")
        params = command.get("params", {})

        # 健康检查不需要连接 CDP
        if action == "health":
            return {
                "success": True,
                "status": "healthy",
                "cdp_connected": self.cdp_client is not None
            }

        # 确保 CDP 已连接
        if not self.cdp_client or self.cdp_client.ws is None:
            self.cdp_client = CDPClient()
            await self.cdp_client.connect()

        # 根据 action 执行操作
        if action == "get_dom":
            return await self._cmd_get_dom()
        elif action == "click":
            return await self._cmd_click(params)
        elif action == "type":
            return await self._cmd_type(params)
        elif action == "scroll":
            return await self._cmd_scroll(params)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "supported_actions": list(self.SUPPORTED_ACTIONS.keys())
            }

    async def _cmd_get_dom(self) -> dict:
        """获取 DOM 树"""
        try:
            dom = await self.cdp_client.get_dom()
            return {
                "success": True,
                "action": "get_dom",
                "dom": dom
            }
        except Exception as e:
            return {
                "success": False,
                "action": "get_dom",
                "error": str(e)
            }

    async def _cmd_click(self, params: dict) -> dict:
        """点击操作"""
        x = params.get("x")
        y = params.get("y")

        if x is None or y is None:
            return {
                "success": False,
                "action": "click",
                "error": "Missing required params: x, y"
            }

        try:
            human = params.get("human", True)
            result = await self.cdp_client.click(x, y, human=human)
            return {
                "success": True,
                "action": "click",
                "target": (x, y),
                "human_simulated": human
            }
        except Exception as e:
            return {
                "success": False,
                "action": "click",
                "error": str(e)
            }

    async def _cmd_type(self, params: dict) -> dict:
        """输入文本"""
        text = params.get("text")
        if not text:
            return {
                "success": False,
                "action": "type",
                "error": "Missing required param: text"
            }

        try:
            await self.cdp_client.type_text(text)
            return {
                "success": True,
                "action": "type",
                "text": text
            }
        except Exception as e:
            return {
                "success": False,
                "action": "type",
                "error": str(e)
            }

    async def _cmd_scroll(self, params: dict) -> dict:
        """滚动页面"""
        x = params.get("x", 0)
        y = params.get("y", 0)
        delta_x = params.get("deltaX", 0)
        delta_y = params.get("deltaY", 100)

        try:
            await self.cdp_client.scroll(x, y, delta_x, delta_y)
            return {
                "success": True,
                "action": "scroll"
            }
        except Exception as e:
            return {
                "success": False,
                "action": "scroll",
                "error": str(e)
            }

    async def cleanup(self):
        """清理资源"""
        if self.cdp_client:
            await self.cdp_client.close()
            self.cdp_client = None


def read_native_message() -> Optional[dict]:
    """
    从 stdin 读取 Native Messaging 消息

    Native Messaging 协议:
    - 消息以 4 字节长度前缀开始（小端序）
    - 后续是 JSON 字符串
    """
    try:
        # 读取 4 字节长度前缀
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            return None

        # 解析长度
        length = int.from_bytes(raw_length, 'little')

        # 读取消息体
        message_bytes = sys.stdin.buffer.read(length)
        if not message_bytes:
            return None

        # 解析 JSON
        return json.loads(message_bytes.decode('utf-8'))

    except Exception as e:
        print(f"Error reading message: {e}", file=sys.stderr)
        return None


def write_native_message(message: dict) -> bool:
    """
    向 stdout 写入 Native Messaging 消息

    返回:
        是否写入成功
    """
    try:
        message_json = json.dumps(message)
        message_bytes = message_json.encode('utf-8')

        # 写入 4 字节长度前缀
        sys.stdout.buffer.write(len(message_bytes).to_bytes(4, 'little'))
        # 写入消息体
        sys.stdout.buffer.write(message_bytes)
        sys.stdout.buffer.flush()

        return True

    except Exception as e:
        print(f"Error writing message: {e}", file=sys.stderr)
        return False


async def main():
    """Native Messaging Host 主循环"""
    print("Neurone Native Host started", file=sys.stderr)

    host = NeuroneHost()

    try:
        while True:
            # 读取消息
            command = read_native_message()
            if command is None:
                break

            # 处理命令
            response = await host.handle_command(command)

            # 发送响应
            write_native_message(response)

    except KeyboardInterrupt:
        print("Neurone Native Host stopped", file=sys.stderr)

    finally:
        await host.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
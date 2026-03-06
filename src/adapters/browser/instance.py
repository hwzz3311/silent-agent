"""
浏览器实例数据类

定义单个浏览器实例的数据结构。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .factory import BrowserMode


@dataclass
class BrowserInstance:
    """单个浏览器实例"""

    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """实例 ID (UUID)"""

    mode: BrowserMode = BrowserMode.HYBRID
    """浏览器模式 (extension/puppeteer/hybrid)"""

    secret_key: Optional[str] = None
    """扩展密钥（Extension/Hybrid 模式用）"""

    ws_endpoint: Optional[str] = None
    """WebSocket 端点（Puppeteer/Hybrid 模式用）"""

    relay_host: str = "127.0.0.1"
    """Relay 服务器主机"""

    relay_port: int = 18792
    """Relay 服务器端口"""

    is_connected: bool = False
    """连接状态"""

    client: Optional[object] = None
    """浏览器客户端实例"""

    created_at: datetime = field(default_factory=datetime.utcnow)
    """创建时间"""

    def to_dict(self) -> dict:
        """转换为字典（不包含客户端）"""
        return {
            "instance_id": self.instance_id,
            "mode": self.mode.value,
            "secret_key": self.secret_key[:8] + "..." if self.secret_key else None,
            "ws_endpoint": self.ws_endpoint,
            "relay_host": self.relay_host,
            "relay_port": self.relay_port,
            "is_connected": self.is_connected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


__all__ = ["BrowserInstance"]

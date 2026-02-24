"""
录制存储模块

提供录制数据的存储、索引和文件读写功能。
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RecordedAction:
    """录制动作"""
    id: str
    type: str  # click, input, scroll, keydown, etc.
    timestamp: int
    offset: int  # 相对开始时间的偏移（毫秒）
    pageUrl: str
    target: Dict[str, Any]  # {selector, tag, text, role, etc.}
    params: Dict[str, Any]  # 事件参数
    position: Dict[str, int]  # {x, y, screenX, screenY}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "offset": self.offset,
            "pageUrl": self.pageUrl,
            "target": self.target,
            "params": self.params,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecordedAction':
        return cls(
            id=data["id"],
            type=data["type"],
            timestamp=data["timestamp"],
            offset=data["offset"],
            pageUrl=data["pageUrl"],
            target=data["target"],
            params=data["params"],
            position=data["position"],
        )


@dataclass
class RecordingMetadata:
    """录制元数据"""
    id: str
    name: str
    startTime: str
    endTime: str
    duration: int  # 毫秒
    pageUrl: str
    pageTitle: str
    actionCount: int
    tags: List[str] = field(default_factory=list)
    description: str = ""
    createdAt: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updatedAt: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "duration": self.duration,
            "pageUrl": self.pageUrl,
            "pageTitle": self.pageTitle,
            "actionCount": self.actionCount,
            "tags": self.tags,
            "description": self.description,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecordingMetadata':
        return cls(
            id=data["id"],
            name=data["name"],
            startTime=data["startTime"],
            endTime=data["endTime"],
            duration=data["duration"],
            pageUrl=data["pageUrl"],
            pageTitle=data["pageTitle"],
            actionCount=data["actionCount"],
            tags=data.get("tags", []),
            description=data.get("description", ""),
            createdAt=data.get("createdAt", datetime.utcnow().isoformat()),
            updatedAt=data.get("updatedAt", datetime.utcnow().isoformat()),
        )


class Recording:
    """录制数据"""

    def __init__(
        self,
        actions: List[RecordedAction] = None,
        metadata: RecordingMetadata = None,
    ):
        self.actions = actions or []
        self.metadata = metadata or self._create_default_metadata()

    def _create_default_metadata(self) -> RecordingMetadata:
        """创建默认元数据"""
        return RecordingMetadata(
            id=str(uuid.uuid4()),
            name=f"Recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            startTime="",
            endTime="",
            duration=0,
            pageUrl="",
            pageTitle="",
            actionCount=len(self.actions),
        )

    @property
    def action_count(self) -> int:
        return len(self.actions)

    def add_action(self, action: RecordedAction) -> None:
        """添加动作"""
        self.actions.append(action)
        self.metadata.actionCount = len(self.actions)

    def add_actions(self, actions: List[RecordedAction]) -> None:
        """批量添加动作"""
        self.actions.extend(actions)
        self.metadata.actionCount = len(self.actions)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metadata": self.metadata.to_dict(),
            "actions": [action.to_dict() for action in self.actions],
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Recording':
        """从字典创建"""
        metadata = RecordingMetadata.from_dict(data.get("metadata", {}))
        actions = [RecordedAction.from_dict(a) for a in data.get("actions", [])]
        return cls(actions=actions, metadata=metadata)

    @classmethod
    def from_json(cls, json_str: str) -> 'Recording':
        """从 JSON 字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class RecordingStorage:
    """
    录制存储

    提供录制数据的本地文件存储和管理功能。

    Attributes:
        storage_dir: 存储目录
    """

    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or self._default_storage_dir())
        self._ensure_storage_dir()

    def _default_storage_dir(self) -> str:
        """获取默认存储目录"""
        home = Path.home()
        return str(home / ".neurone" / "recordings")

    def _ensure_storage_dir(self) -> None:
        """确保存储目录存在"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, recording: Recording) -> str:
        """
        保存录制

        Args:
            recording: 录制数据

        Returns:
            录制 ID
        """
        # 更新元数据
        if not recording.metadata.id:
            recording.metadata.id = str(uuid.uuid4())
        recording.metadata.updatedAt = datetime.utcnow().isoformat()

        # 生成文件名
        filename = f"{recording.metadata.id}.json"
        filepath = self.storage_dir / filename

        # 写入文件
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(recording.to_json())

        return recording.metadata.id

    def load(self, recording_id: str) -> Optional[Recording]:
        """
        加载录制

        Args:
            recording_id: 录制 ID

        Returns:
            录制数据，不存在则返回 None
        """
        filepath = self.storage_dir / f"{recording_id}.json"
        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Recording.from_dict(data)

    def load_by_name(self, name: str) -> Optional[Recording]:
        """
        根据名称加载录制

        Args:
            name: 录制名称

        Returns:
            录制数据，不存在则返回 None
        """
        for filepath in self.storage_dir.glob("*.json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("metadata", {}).get("name") == name:
                    return Recording.from_dict(data)
        return None

    def delete(self, recording_id: str) -> bool:
        """
        删除录制

        Args:
            recording_id: 录制 ID

        Returns:
            是否删除成功
        """
        filepath = self.storage_dir / f"{recording_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def list_all(self) -> List[RecordingMetadata]:
        """
        列出所有录制

        Returns:
            录制元数据列表
        """
        recordings = []
        for filepath in sorted(self.storage_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    recordings.append(RecordingMetadata.from_dict(data.get("metadata", {})))
            except Exception as e:
                print(f"[RecordingStorage] 加载录制失败 {filepath}: {e}")
        return recordings

    def list_by_tag(self, tag: str) -> List[RecordingMetadata]:
        """
        按标签列出录制

        Args:
            tag: 标签

        Returns:
            匹配的录制元数据列表
        """
        return [r for r in self.list_all() if tag in r.tags]

    def search(self, query: str) -> List[RecordingMetadata]:
        """
        搜索录制

        Args:
            query: 搜索关键词

        Returns:
            匹配的录制元数据列表
        """
        query_lower = query.lower()
        return [
            r for r in self.list_all()
            if query_lower in r.name.lower() or
               query_lower in r.pageTitle.lower() or
               query_lower in r.pageUrl.lower()
        ]

    def update_metadata(self, recording_id: str, metadata: Dict[str, Any]) -> bool:
        """
        更新录制元数据

        Args:
            recording_id: 录制 ID
            metadata: 更新的元数据

        Returns:
            是否更新成功
        """
        recording = self.load(recording_id)
        if not recording:
            return False

        # 更新字段
        if "name" in metadata:
            recording.metadata.name = metadata["name"]
        if "description" in metadata:
            recording.metadata.description = metadata["description"]
        if "tags" in metadata:
            recording.metadata.tags = metadata["tags"]

        recording.metadata.updatedAt = datetime.utcnow().isoformat()
        self.save(recording)
        return True

    def add_tag(self, recording_id: str, tag: str) -> bool:
        """
        添加标签

        Args:
            recording_id: 录制 ID
            tag: 标签

        Returns:
            是否添加成功
        """
        recording = self.load(recording_id)
        if not recording:
            return False

        if tag not in recording.metadata.tags:
            recording.metadata.tags.append(tag)
            recording.metadata.updatedAt = datetime.utcnow().isoformat()
            self.save(recording)

        return True

    def get_storage_dir(self) -> str:
        """获取存储目录"""
        return str(self.storage_dir)


# ========== 便捷函数 ==========

def create_storage(storage_dir: str = None) -> RecordingStorage:
    """创建存储实例"""
    return RecordingStorage(storage_dir)


__all__ = [
    "RecordedAction",
    "RecordingMetadata",
    "Recording",
    "RecordingStorage",
    "create_storage",
]
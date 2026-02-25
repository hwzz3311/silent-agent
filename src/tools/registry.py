"""
工具注册表模块

提供工具注册、发现、查询和管理功能。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from src.tools.base import Tool, ToolInfo


class ToolCategory(str, Enum):
    """工具分类"""
    BROWSER = "browser"
    DATA = "data"
    NETWORK = "network"
    UTILITY = "utility"
    CUSTOM = "custom"
    SYSTEM = "system"


@dataclass
class ToolVersion:
    """工具版本信息"""
    version: str
    released_at: datetime = field(default_factory=datetime.utcnow)
    changelog: str = ""
    compatible_from: str = "1.0.0"  # 兼容的最低版本


@dataclass
class ToolMetadata:
    """工具元数据"""
    info: ToolInfo
    category: ToolCategory = ToolCategory.UTILITY
    author: str = "unknown"
    license: str = "MIT"
    home_url: str = ""
    source_url: str = ""
    dependencies: List[str] = field(default_factory=list)
    versions: Dict[str, ToolVersion] = field(default_factory=dict)
    is_deprecated: bool = False
    deprecated_version: str = ""
    replacement: str = ""  # 替代工具名称

    @property
    def current_version(self) -> str:
        """获取当前版本"""
        return self.info.version


class ToolRegistry:
    """
    工具注册表

    提供工具的注册、查询、版本管理等功能。
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}
        self._tags_index: Dict[str, List[str]] = {}  # tag -> tool names

    # ========== 注册/注销 ==========

    def register(self, tool: Tool, metadata: ToolMetadata = None) -> None:
        """
        注册工具

        Args:
            tool: 工具实例
            metadata: 工具元数据（可选）
        """
        name = tool.name

        if name in self._tools:
            raise ValueError(f"工具已注册: {name}")

        # 注册工具
        self._tools[name] = tool

        # 创建默认元数据（如果未提供）
        if metadata is None:
            metadata = ToolMetadata(
                info=tool.get_info(),
                category=self._infer_category(name),
            )
        self._metadata[name] = metadata

        # 更新分类索引
        category = metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

        # 更新标签索引
        for tag in tool.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = []
            if name not in self._tags_index[tag]:
                self._tags_index[tag].append(name)

    def unregister(self, name: str) -> Tool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            被注销的工具实例
        """
        if name not in self._tools:
            raise ValueError(f"工具未注册: {name}")

        tool = self._tools.pop(name)
        metadata = self._metadata.pop(name)

        # 从分类索引中移除
        category = metadata.category
        if category in self._categories and name in self._categories[category]:
            self._categories[category].remove(name)

        # 从标签索引中移除
        for tag in tool.tags:
            if tag in self._tags_index and name in self._tags_index[tag]:
                self._tags_index[tag].remove(name)

        return tool

    def update_metadata(self, name: str, metadata: ToolMetadata) -> None:
        """更新工具元数据"""
        if name not in self._tools:
            raise ValueError(f"工具未注册: {name}")
        self._metadata[name] = metadata

    # ========== 查询 ==========

    def get(self, name: str) -> Optional[Tool]:
        """获取工具实例"""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """获取工具元数据"""
        return self._metadata.get(name)

    def get_info(self, name: str) -> Optional[ToolInfo]:
        """获取工具信息"""
        metadata = self._metadata.get(name)
        return metadata.info if metadata else None

    def exists(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools

    def is_registered(self, name: str) -> bool:
        """检查工具是否已注册"""
        return self.exists(name)

    # ========== 列表查询 ==========

    def list_all(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())

    def list_by_category(self, category: ToolCategory) -> List[str]:
        """按分类列出工具"""
        return self._categories.get(category, [])

    def list_by_tag(self, tag: str) -> List[str]:
        """按标签列出工具"""
        return self._tags_index.get(tag, [])

    def list_builtin(self) -> List[str]:
        """列出内置工具"""
        return [name for name, tool in self._tools.items() if getattr(tool, 'is_builtin', False)]

    def list_deprecated(self) -> List[str]:
        """列出已废弃的工具"""
        return [name for name, meta in self._metadata.items() if meta.is_deprecated]

    def list_with_version(self, version: str) -> List[str]:
        """列出指定版本的工具"""
        result = []
        for name, meta in self._metadata.items():
            if version in meta.versions:
                result.append(name)
        return result

    # ========== 搜索 ==========

    def search(self, query: str, limit: int = 20) -> List[str]:
        """
        搜索工具

        Args:
            query: 搜索关键词
            limit: 结果数量限制

        Returns:
            匹配的工具名称列表
        """
        query_lower = query.lower()
        results = []

        for name, info in self._metadata.items():
            # 检查名称
            if query_lower in name.lower():
                results.append(name)
                continue

            # 检查描述
            if query_lower in info.info.description.lower():
                results.append(name)
                continue

            # 检查标签
            for tag in info.info.tags:
                if query_lower in tag.lower():
                    results.append(name)
                    break

        return results[:limit]

    def fuzzy_search(self, query: str, limit: int = 10) -> List[str]:
        """模糊搜索工具"""
        import difflib

        query_lower = query.lower()
        tools = list(self._tools.keys())

        # 计算相似度
        scores = []
        for name in tools:
            ratio = difflib.SequenceMatcher(None, query_lower, name.lower()).ratio()
            scores.append((name, ratio))

        # 按相似度排序
        scores.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scores[:limit]]

    # ========== 版本管理 ==========

    def register_version(self, name: str, version: str, changelog: str = "") -> None:
        """注册工具版本"""
        if name not in self._tools:
            raise ValueError(f"工具未注册: {name}")

        metadata = self._metadata[name]
        metadata.versions[version] = ToolVersion(
            version=version,
            changelog=changelog,
        )

    def get_version_history(self, name: str) -> List[ToolVersion]:
        """获取工具版本历史"""
        if name not in self._metadata:
            raise ValueError(f"工具未注册: {name}")

        versions = self._metadata[name].versions
        return sorted(versions.values(), key=lambda v: v.released_at, reverse=True)

    # ========== 工具描述接口 ==========

    def get_tool_schema(self, name: str) -> Dict[str, Any]:
        """获取工具的 JSON Schema"""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"工具未注册: {name}")

        return {
            "name": name,
            "description": tool.description,
            "version": tool.version,
            "category": self._metadata[name].category.value if name in self._metadata else "utility",
            "parameters": tool.get_parameters_schema(),
            "returns": tool.get_returns_schema(),
        }

    def list_tool_schemas(self) -> List[Dict[str, Any]]:
        """列出所有工具的 Schema"""
        return [self.get_tool_schema(name) for name in self._tools.keys()]

    # ========== 内部方法 ==========

    def _infer_category(self, name: str) -> ToolCategory:
        """推断工具分类"""
        name_lower = name.lower()

        if name_lower.startswith(("browser.", "chrome.", "a11y")):
            return ToolCategory.BROWSER
        elif name_lower.startswith(("http.", "network.")):
            return ToolCategory.NETWORK
        elif name_lower.startswith(("data.", "file.", "json.")):
            return ToolCategory.DATA
        elif name_lower.startswith(("system.", "os.")):
            return ToolCategory.SYSTEM
        else:
            return ToolCategory.UTILITY

    # ========== 统计信息 ==========

    def get_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        return {
            "total_tools": len(self._tools),
            "categories": {
                cat.value: len(tools)
                for cat, tools in self._categories.items()
            },
            "builtin_count": len(self.list_builtin()),
            "deprecated_count": len(self.list_deprecated()),
            "tag_count": len(self._tags_index),
        }

    def export_registry(self) -> Dict[str, Any]:
        """导出注册表数据"""
        # Pydantic v2+ uses model_dump, v1 uses dict
        def dump_info(info):
            if hasattr(info, 'model_dump'):
                return info.model_dump()
            else:
                return info.dict()

        return {
            "tools": {
                name: {
                    "info": dump_info(meta.info),
                    "category": meta.category.value,
                    "author": meta.author,
                    "is_deprecated": meta.is_deprecated,
                }
                for name, meta in self._metadata.items()
            },
            "stats": self.get_stats(),
        }

    # ========== 批量操作 ==========

    def register_many(self, tools: List[Tool]) -> None:
        """批量注册工具"""
        for tool in tools:
            self.register(tool)

    def clear(self) -> None:
        """清空注册表"""
        self._tools.clear()
        self._metadata.clear()
        self._categories.clear()
        self._tags_index.clear()


# ========== 全局注册表 ==========

# 默认全局注册表实例
default_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """获取默认注册表"""
    return default_registry


def register_tool(tool: Tool, metadata: ToolMetadata = None) -> None:
    """注册工具到默认注册表"""
    default_registry.register(tool, metadata)


def unregister_tool(name: str) -> Tool:
    """从默认注册表注销工具"""
    return default_registry.unregister(name)


def get_tool(name: str) -> Optional[Tool]:
    """从默认注册表获取工具"""
    return default_registry.get(name)


def list_tools() -> List[str]:
    """列出默认注册表中的所有工具"""
    return default_registry.list_all()


def search_tools(query: str) -> List[str]:
    """在默认注册表中搜索工具"""
    return default_registry.search(query)


# ========== 便捷类装饰器 ==========

class tool:
    """工具类装饰器，自动注册到默认注册表"""

    def __init__(
        self,
        name: str = None,
        description: str = "",
        category: ToolCategory = ToolCategory.UTILITY,
        version: str = "1.0.0",
        tags: List[str] = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.version = version
        self.tags = tags or []

    def __call__(self, cls):
        # 设置工具属性
        if self.name:
            cls.name = self.name
        cls.description = self.description or cls.__doc__ or ""
        cls.category = self.category.value if isinstance(self.category, ToolCategory) else self.category
        cls.version = self.version
        cls.tags = self.tags
        cls.is_builtin = True

        # 注册到默认注册表
        register_tool(cls())
        return cls


__all__ = [
    "ToolRegistry",
    "ToolMetadata",
    "ToolCategory",
    "default_registry",
    "get_registry",
    "register_tool",
    "unregister_tool",
    "get_tool",
    "list_tools",
    "search_tools",
    "tool",
]
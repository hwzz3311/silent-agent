"""
录制回放模块

提供录制数据的回放功能。
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List

from .storage import RecordedAction, Recording, RecordingStorage
from .adapter import SelectorAdapter, ElementMatcher


class PlaybackState:
    """回放状态"""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PlaybackConfig:
    """回放配置"""
    speed: float = 1.0  # 播放速度（1.0 = 正常速度）
    skip_delays: bool = True  # 是否跳过延迟
    skip_screenshots: bool = True  # 是否跳过截图
    retry_on_error: bool = True  # 错误时是否重试
    retry_count: int = 3  # 重试次数
    retry_delay: int = 1000  # 重试间隔（毫秒）
    use_fallback_selectors: bool = True  # 是否使用备用选择器
    use_a11y_tree: bool = True  # 是否使用无障碍树
    on_action: Callable[[RecordedAction, int], None] = None  # 动作回调
    on_error: Callable[[RecordedAction, Exception], None] = None  # 错误回调
    on_complete: Callable[[], None] = None  # 完成回调
    on_skip: Callable[[RecordedAction, str], None] = None  # 跳过回调


@dataclass
class PlaybackResult:
    """回放结果"""

    def __init__(
        self,
        success: bool,
        recording_id: str,
        state: str,
        actions_count: int = 0,
        actions_completed: int = 0,
        actions_skipped: int = 0,
        errors: List[Dict[str, Any]] = None,
        duration_ms: int = 0,
        selector_fallbacks: int = 0,
    ):
        self.success = success
        self.recording_id = recording_id
        self.state = state
        self.actions_count = actions_count
        self.actions_completed = actions_completed
        self.actions_skipped = actions_skipped
        self.errors = errors or []
        self.duration_ms = duration_ms
        self.selector_fallbacks = selector_fallbacks
        self.start_time = None
        self.end_time = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "recording_id": self.recording_id,
            "state": self.state,
            "actions_count": self.actions_count,
            "actions_completed": self.actions_completed,
            "actions_skipped": self.actions_skipped,
            "selector_fallbacks": self.selector_fallbacks,
            "errors": self.errors,
            "duration_ms": self.duration_ms,
        }

    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.actions_count == 0:
            return 0.0
        return len(self.errors) / self.actions_count

    @property
    def completion_rate(self) -> float:
        """完成率"""
        if self.actions_count == 0:
            return 0.0
        return self.actions_completed / self.actions_count


class RecordingPlayer:
    """
    录制回放器

    负责执行录制的操作序列。

    Attributes:
        config: 回放配置
        state: 当前状态
        current_action_index: 当前动作索引
        selector_adapter: 选择器适配器
        element_matcher: 元素匹配器
    """

    def __init__(self, config: PlaybackConfig = None):
        self.config = config or PlaybackConfig()
        self.state = PlaybackState.IDLE
        self.current_action_index = 0
        self._cancelled = False
        self._paused = False
        self.selector_adapter = SelectorAdapter()
        self.element_matcher = ElementMatcher(self.selector_adapter)
        self._selector_fallbacks = 0

    @property
    def is_playing(self) -> bool:
        return self.state == PlaybackState.PLAYING

    @property
    def is_paused(self) -> bool:
        return self.state == PlaybackState.PAUSED

    @property
    def is_completed(self) -> bool:
        return self.state == PlaybackState.COMPLETED

    @property
    def fallback_count(self) -> int:
        """备用选择器使用次数"""
        return self._selector_fallbacks

    async def play(
        self,
        recording: Recording,
        tool_caller: Callable[[str, Dict], Any],
        element_finder: Callable[[str], Any] = None,
    ) -> PlaybackResult:
        """
        播放录制

        Args:
            recording: 录制数据
            tool_caller: 工具调用函数 (tool_name, params) -> Result
            element_finder: 元素查找函数 (selector) -> element（可选）

        Returns:
            PlaybackResult: 回放结果
        """
        if self.is_playing:
            raise ValueError("已经在播放中")

        self.state = PlaybackState.PLAYING
        self.current_action_index = 0
        self._cancelled = False
        self._paused = False
        self._selector_fallbacks = 0

        errors = []
        skipped = []
        actions_completed = 0
        start_time = datetime.utcnow()

        try:
            for i, action in enumerate(recording.actions):
                if self._cancelled:
                    self.state = PlaybackState.CANCELLED
                    break

                # 等待暂停恢复
                while self._paused and not self._cancelled:
                    await asyncio.sleep(0.1)

                if self._cancelled:
                    self.state = PlaybackState.CANCELLED
                    break

                # 执行动作
                try:
                    await self._play_action(action, tool_caller, element_finder)
                    actions_completed += 1

                    # 动作回调
                    if self.config.on_action:
                        self.config.on_action(action, i)

                except Exception as e:
                    error_info = {
                        "action_id": action.id,
                        "action_type": action.type,
                        "action_index": i,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat(),
                        "selector": action.target.get("selector"),
                    }

                    # 决定是否重试
                    if self.config.retry_on_error:
                        success = await self._retry_action(
                            action, tool_caller, element_finder, error_info, errors
                        )
                        if success:
                            actions_completed += 1
                        else:
                            errors.append(error_info)
                    else:
                        errors.append(error_info)

                    # 错误回调
                    if self.config.on_error:
                        self.config.on_error(action, e)

            if not self._cancelled:
                self.state = PlaybackState.COMPLETED

        except asyncio.CancelledError:
            self.state = PlaybackState.CANCELLED
            raise

        finally:
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return PlaybackResult(
            success=len(errors) == 0,
            recording_id=recording.metadata.id,
            state=self.state,
            actions_count=len(recording.actions),
            actions_completed=actions_completed,
            actions_skipped=len(skipped),
            errors=errors,
            duration_ms=duration_ms,
            selector_fallbacks=self._selector_fallbacks,
        )

    async def _retry_action(
        self,
        action: RecordedAction,
        tool_caller: Callable[[str, Dict], Any],
        element_finder: Callable[[str], Any],
        error_info: Dict[str, Any],
        errors: List[Dict[str, Any]],
    ) -> bool:
        """重试执行动作"""
        for retry in range(1, self.config.retry_count):
            await asyncio.sleep(self.config.retry_delay / 1000)
            try:
                await self._play_action(action, tool_caller, element_finder)
                return True
            except Exception:
                continue
        return False

    async def _play_action(
        self,
        action: RecordedAction,
        tool_caller: Callable[[str, Dict], Any],
        element_finder: Callable[[str], Any] = None,
    ) -> None:
        """执行单个动作"""
        action_type = action.type
        target = action.target
        params = action.params
        fallback_used = False

        # 根据动作类型执行相应的工具调用
        if action_type == "click":
            # 使用选择器适配
            selector = self._resolve_selector(
                target.get("selector"),
                target,
                element_finder,
            )
            await tool_caller("browser.click", {
                "selector": selector,
                "text": target.get("text"),
            })
            if selector != target.get("selector"):
                fallback_used = True

        elif action_type == "double_click":
            selector = self._resolve_selector(
                target.get("selector"),
                target,
                element_finder,
            )
            await tool_caller("browser.click", {
                "selector": selector,
                "count": 2,
            })
            if selector != target.get("selector"):
                fallback_used = True

        elif action_type in ("input", "change"):
            selector = self._resolve_selector(
                target.get("selector"),
                target,
                element_finder,
            )
            await tool_caller("browser.fill", {
                "selector": selector,
                "value": params.get("value", ""),
            })
            if selector != target.get("selector"):
                fallback_used = True

        elif action_type in ("keydown", "keyup"):
            key = params.get("key", "")
            modifiers = []
            if params.get("ctrlKey"): modifiers.append("Control")
            if params.get("altKey"): modifiers.append("Alt")
            if params.get("shiftKey"): modifiers.append("Shift")
            if params.get("metaKey"): modifiers.append("Meta")

            if modifiers:
                keys = ",".join(modifiers + [key])
            else:
                keys = key

            await tool_caller("browser.keyboard", {
                "keys": keys,
                "selector": target.get("selector"),
            })

        elif action_type == "scroll":
            await tool_caller("browser.scroll", {
                "direction": "down",
                "amount": abs(params.get("deltaY", 300)),
                "selector": target.get("selector"),
            })

        elif action_type == "navigate":
            await tool_caller("browser.navigate", {
                "url": action.pageUrl,
            })

        elif action_type == "wait":
            await tool_caller("browser.wait", {
                "selector": target.get("selector"),
                "timeout": params.get("timeout", 5000),
            })

        else:
            # 未知动作类型，尝试作为 click 处理
            if target.get("selector"):
                selector = self._resolve_selector(
                    target.get("selector"),
                    target,
                    element_finder,
                )
                await tool_caller("browser.click", {
                    "selector": selector,
                })
                if selector != target.get("selector"):
                    fallback_used = True

        if fallback_used:
            self._selector_fallbacks += 1

    def _resolve_selector(
        self,
        selector: str,
        target_info: Dict[str, Any],
        element_finder: Callable[[str], Any] = None,
    ) -> str:
        """
        解析选择器，如果原始选择器找不到元素，使用备用选择器

        Args:
            selector: 原始选择器
            target_info: 目标元素信息
            element_finder: 元素查找函数

        Returns:
            最终使用的选择器
        """
        if not self.config.use_fallback_selectors:
            return selector

        if not element_finder:
            return selector

        # 检查原始选择器是否有效
        try:
            element = element_finder(selector)
            if element:
                return selector
        except Exception:
            pass

        # 生成备用选择器
        fallback_selectors = self.selector_adapter.generate_fallback_selectors(
            selector,
            target_info,
        )

        # 尝试备用选择器
        for fallback in fallback_selectors:
            try:
                element = element_finder(fallback)
                if element:
                    return fallback
            except Exception:
                continue

        # 如果都找不到，使用原始选择器
        return selector


class RecordingReplay:
    """
    录制回放管理器

    提供录制数据的加载、配置和回放功能。

    Attributes:
        storage: 录制存储
        player: 录制回放器
    """

    def __init__(self, storage_dir: str = None):
        self.storage = RecordingStorage(storage_dir)
        self.player = RecordingPlayer()

    async def load_and_play(
        self,
        recording_id: str = None,
        recording_name: str = None,
        tool_caller: Callable[[str, Dict], Any] = None,
        config: PlaybackConfig = None,
        element_finder: Callable[[str], Any] = None,
    ) -> PlaybackResult:
        """
        加载录制并回放

        Args:
            recording_id: 录制 ID
            recording_name: 录制名称
            tool_caller: 工具调用函数
            config: 回放配置
            element_finder: 元素查找函数

        Returns:
            PlaybackResult: 回放结果
        """
        # 加载录制
        if recording_id:
            recording = self.storage.load(recording_id)
        elif recording_name:
            recording = self.storage.load_by_name(recording_name)
        else:
            raise ValueError("需要提供 recording_id 或 recording_name")

        if not recording:
            raise ValueError(f"录制不存在: {recording_id or recording_name}")

        # 配置回放器
        if config:
            self.player.config = config

        # 播放
        return await self.player.play(recording, tool_caller, element_finder)

    def get_recordings(self) -> List:
        """获取所有录制"""
        return self.storage.list_all()

    def search_recordings(self, query: str) -> List:
        """搜索录制"""
        return self.storage.search(query)

    def get_recording(self, recording_id: str):
        """获取录制"""
        return self.storage.load(recording_id)

    def delete_recording(self, recording_id: str) -> bool:
        """删除录制"""
        return self.storage.delete(recording_id)


# ========== 便捷函数 ==========

def create_player(config: PlaybackConfig = None) -> RecordingPlayer:
    """创建回放器"""
    return RecordingPlayer(config)


def create_replay(storage_dir: str = None) -> RecordingReplay:
    """创建回放管理器"""
    return RecordingReplay(storage_dir)


__all__ = [
    "PlaybackState",
    "PlaybackConfig",
    "PlaybackResult",
    "RecordingPlayer",
    "RecordingReplay",
    "create_player",
    "create_replay",
]
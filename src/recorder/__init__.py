"""
录制回放模块

提供录制数据的存储和回放功能。

使用示例:
```python
from recorder import Recording, RecordingStorage, RecordingReplay, PlaybackConfig

# 创建存储
storage = RecordingStorage()

# 加载录制
recording = storage.load("recording_id")

# 创建回放配置
config = PlaybackConfig(
    speed=2.0,  # 2倍速
    skip_delays=True,  # 跳过延迟
    on_action=lambda action, index: print(f"执行动作: {action.type}"),
)

# 创建回放器并播放
player = RecordingPlayer(config)
result = await player.play(recording, tool_caller)
print(f"回放结果: {result.success}")
```
"""

from .storage import (
    RecordedAction,
    RecordingMetadata,
    Recording,
    RecordingStorage,
    create_storage,
)

from .adapter import (
    SelectorAdapter,
    ElementMatcher,
    ElementInfoExtractor,
    create_adapter,
    create_matcher,
    extract_info,
)

from .player import (
    PlaybackState,
    PlaybackConfig,
    PlaybackResult,
    RecordingPlayer,
    RecordingReplay,
    create_player,
    create_replay,
)

from .optimizer import (
    RecordingOptimizer,
    optimize_recording,
)

__all__ = [
    # Storage
    "RecordedAction",
    "RecordingMetadata",
    "Recording",
    "RecordingStorage",
    "create_storage",
    # Adapter
    "SelectorAdapter",
    "ElementMatcher",
    "ElementInfoExtractor",
    "create_adapter",
    "create_matcher",
    "extract_info",
    # Player
    "PlaybackState",
    "PlaybackConfig",
    "PlaybackResult",
    "RecordingPlayer",
    "RecordingReplay",
    "create_player",
    "create_replay",
    # Optimizer
    "RecordingOptimizer",
    "optimize_recording",
]
"""
录制优化器

提供录制操作序列的优化功能，包括 AI 优化和手动优化。
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re

from .storage import Recording, RecordingStorage


class RecordingOptimizer:
    """
    录制优化器

    提供录制操作序列的优化功能。
    """

    def __init__(self):
        """初始化优化器"""
        self.optimization_rules = [
            self._remove_redundant_waits,
            self._merge_consecutive_clicks,
            self._optimize_selectors,
            self._remove_duplicate_actions,
        ]

    async def optimize(
        self,
        recording_id: str,
        instructions: str = None
    ) -> Dict[str, Any]:
        """
        优化录制

        Args:
            recording_id: 录制 ID
            instructions: 优化指令（可选）

        Returns:
            优化结果
        """
        # 加载录制
        storage = RecordingStorage()
        recording = storage.get_recording(recording_id)

        if not recording:
            return {
                "success": False,
                "error": f"录制不存在: {recording_id}"
            }

        original_count = len(recording.actions)
        changes = []

        # 应用优化规则
        optimized_actions = recording.actions.copy()

        for rule in self.optimization_rules:
            optimized_actions, rule_changes = rule(optimized_actions)
            changes.extend(rule_changes)

        # 如果有 AI 优化指令，应用 AI 优化
        if instructions:
            ai_changes = await self._apply_ai_optimization(
                optimized_actions,
                instructions
            )
            changes.extend(ai_changes)

        # 创建优化后的录制
        optimized_recording = Recording(
            id=f"{recording_id}_optimized",
            name=recording.name,
            description=f"优化后的录制 (原始: {recording_id})",
            actions=optimized_actions,
            page_url=recording.page_url,
            page_title=recording.page_title,
            tab_id=recording.tab_id,
            created_at=datetime.utcnow(),
            duration_ms=self._calculate_duration(optimized_actions),
        )

        # 保存优化后的录制
        optimized_id = storage.save(optimized_recording)

        return {
            "success": True,
            "original_recording_id": recording_id,
            "optimized_recording_id": optimized_id,
            "original_actions": original_count,
            "optimized_actions": len(optimized_actions),
            "changes_count": len(changes),
            "changes": changes,
            "message": f"优化完成，减少 {original_count - len(optimized_actions)} 个操作"
        }

    def _remove_redundant_waits(
        self,
        actions: List[Dict[str, Any]]
    ) -> (List[Dict[str, Any]], List[Dict[str, Any]]):
        """移除多余的等待操作"""
        optimized = []
        changes = []

        for i, action in enumerate(actions):
            if action.get("type") == "wait" and action.get("duration", 0) < 100:
                changes.append({
                    "type": "remove",
                    "index": i,
                    "action_type": "wait",
                    "reason": "等待时间过短"
                })
                continue
            optimized.append(action)

        return optimized, changes

    def _merge_consecutive_clicks(
        self,
        actions: List[Dict[str, Any]]
    ) -> (List[Dict[str, Any]], List[Dict[str, Any]]):
        """合并连续点击操作"""
        if len(actions) < 2:
            return actions, []

        optimized = [actions[0]]
        changes = []

        for i in range(1, len(actions)):
            current = actions[i]
            previous = optimized[-1]

            # 检查是否是两个连续点击同一元素
            if (current.get("type") == "click" and
                previous.get("type") == "click" and
                current.get("selector") == previous.get("selector")):
                # 保留前一个点击，移除后一个（可能是重复点击）
                changes.append({
                    "type": "remove",
                    "index": i,
                    "action_type": "click",
                    "reason": "连续点击同一元素"
                })
                continue

            optimized.append(current)

        return optimized, changes

    def _optimize_selectors(
        self,
        actions: List[Dict[str, Any]]
    ) -> (List[Dict[str, Any]], List[Dict[str, Any]]):
        """优化选择器"""
        optimized = []
        changes = []

        for i, action in enumerate(actions):
            selector = action.get("selector", "")

            if selector and len(selector) > 100:
                # 简化过长的选择器
                optimized_selector = self._simplify_selector(selector)
                if optimized_selector != selector:
                    changes.append({
                        "type": "modify",
                        "index": i,
                        "field": "selector",
                        "original": selector[:50] + "...",
                        "optimized": optimized_selector[:50] + "...",
                        "reason": "选择器过长"
                    })
                    action = action.copy()
                    action["selector"] = optimized_selector

            optimized.append(action)

        return optimized, changes

    def _remove_duplicate_actions(
        self,
        actions: List[Dict[str, Any]]
    ) -> (List[Dict[str, Any]], List[Dict[str, Any]]):
        """移除重复操作"""
        optimized = []
        changes = []
        seen = set()

        for i, action in enumerate(actions):
            action_key = (action.get("type"), action.get("selector"), action.get("value"))

            if action_key in seen:
                changes.append({
                    "type": "remove",
                    "index": i,
                    "action_type": action.get("type"),
                    "reason": "重复操作"
                })
                continue

            seen.add(action_key)
            optimized.append(action)

        return optimized, changes

    def _simplify_selector(self, selector: str) -> str:
        """简化选择器"""
        # 移除过于具体的选择器部分
        if selector.startswith("[class*='") and len(selector) > 50:
            # 保留较短的选择器
            match = re.search(r"\[class\*='([^']+)'\]", selector)
            if match:
                return f"[class*='{match.group(1)}']"

        return selector

    async def _apply_ai_optimization(
        self,
        actions: List[Dict[str, Any]],
        instructions: str
    ) -> List[Dict[str, Any]]:
        """应用 AI 优化建议"""
        # TODO: 实现 AI 优化
        # 这里可以接入 LLM API 来分析录制并进行优化
        changes = []

        # 示例：根据指令进行简单优化
        if "等待" in instructions or "wait" in instructions.lower():
            for i, action in enumerate(actions):
                if action.get("type") == "wait":
                    changes.append({
                        "type": "modify",
                        "index": i,
                        "field": "duration",
                        "reason": "AI 建议优化"
                    })

        return changes

    def _calculate_duration(self, actions: List[Dict[str, Any]]) -> int:
        """计算总时长"""
        total = 0
        for action in actions:
            total += action.get("duration", 0)
        return total


# 便捷函数
async def optimize_recording(
    recording_id: str,
    instructions: str = None
) -> Dict[str, Any]:
    """
    优化录制

    Args:
        recording_id: 录制 ID
        instructions: 优化指令

    Returns:
        优化结果
    """
    optimizer = RecordingOptimizer()
    return await optimizer.optimize(recording_id, instructions)


__all__ = [
    "RecordingOptimizer",
    "optimize_recording",
]
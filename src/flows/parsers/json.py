"""
流程解析器模块

提供流程定义的数据解析功能。
"""

from typing import Any, Dict, List, Optional

import yaml
from pydantic import ValidationError
from src.flows.steps import StepType, StepConfig


class FlowParser:
    """
    流程解析器

    负责将各种格式的流程定义解析为标准化的数据字典。
    """

    def __init__(self):
        self.step_type_map = {
            "action": StepType.ACTION,
            "condition": StepType.CONDITION,
            "loop": StepType.LOOP,
            "parallel": StepType.PARALLEL,
            "wait": StepType.WAIT,
            "sub_flow": StepType.SUB_FLOW,
            "set_var": StepType.SET_VAR,
            "log": StepType.LOG,
        }

    def parse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析流程定义

        Args:
            data: 原始流程数据

        Returns:
            标准化后的流程数据
        """
        return {
            "id": data.get("id", self._generate_id()),
            "name": data.get("name", "Unnamed Flow"),
            "description": data.get("description"),
            "version": data.get("version", "1.0.0"),
            "variables": self._parse_variables(data.get("variables", [])),
            "steps": self._parse_steps(data.get("steps", [])),
            "timeout": data.get("timeout"),
            "tags": data.get("tags", []),
        }

    def _parse_variables(self, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析变量定义"""
        parsed = []
        for var in variables:
            parsed.append({
                "name": var.get("name"),
                "type": var.get("type", "string"),
                "description": var.get("description"),
                "default": var.get("default"),
                "required": var.get("required", False),
            })
        return parsed

    def _parse_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析步骤定义"""
        parsed = []
        for step in steps:
            parsed.append(self._parse_step(step))
        return parsed

    def _parse_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """解析单个步骤"""
        step_type = step.get("type", "action")
        normalized_type = self.step_type_map.get(step_type, StepType.ACTION)

        parsed = {
            "id": step.get("id", self._generate_id()),
            "name": step.get("name", f"Step {normalized_type.value}"),
            "type": normalized_type.value,
            "config": self._parse_config(step.get("config", {})),
            "next_on_success": step.get("next_on_success"),
            "next_on_failure": step.get("next_on_failure"),
        }

        # 根据步骤类型解析特定字段
        if normalized_type == StepType.ACTION:
            parsed["tool"] = step.get("tool")
            parsed["params"] = step.get("params", {})

        elif normalized_type == StepType.CONDITION:
            parsed["condition"] = step.get("condition")
            parsed["on_true"] = self._parse_steps(step.get("on_true", []))
            parsed["on_false"] = self._parse_steps(step.get("on_false", []))

        elif normalized_type == StepType.LOOP:
            parsed["loop_type"] = step.get("loop_type", "while")
            parsed["condition"] = step.get("condition")
            parsed["items"] = step.get("items", [])
            parsed["loop_var"] = step.get("loop_var", "item")
            parsed["max_iterations"] = step.get("max_iterations", 1000)
            parsed["body"] = self._parse_steps(step.get("body", []))

        elif normalized_type == StepType.WAIT:
            parsed["wait_type"] = step.get("wait_type", "time")
            parsed["duration"] = step.get("duration", 1000)
            parsed["condition"] = step.get("condition")
            parsed["interval"] = step.get("interval", 500)

        elif normalized_type == StepType.SET_VAR:
            parsed["variable"] = step.get("variable")
            parsed["value"] = step.get("value")
            parsed["operation"] = step.get("operation", "set")  # set, inc, dec, etc.

        elif normalized_type == StepType.LOG:
            parsed["message"] = step.get("message")
            parsed["level"] = step.get("level", "info")  # debug, info, warn, error

        return parsed

    def _parse_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """解析步骤配置"""
        return {
            "timeout": config.get("timeout"),
            "retry_count": config.get("retry_count", 1),
            "retry_delay": config.get("retry_delay", 1000),
            "continue_on_error": config.get("continue_on_error", False),
            "condition": config.get("condition"),
        }

    def _generate_id(self) -> str:
        """生成步骤 ID"""
        import uuid
        return f"step_{uuid.uuid4().hex[:8]}"

    def parse_from_yaml(self, yaml_data: str) -> Dict[str, Any]:
        """从 YAML 字符串解析流程"""
        data = yaml.safe_load(yaml_data)
        return self.parse(data)

    def parse_from_json(self, json_data: str) -> Dict[str, Any]:
        """从 JSON 字符串解析流程"""
        import json
        data = json.loads(json_data)
        return self.parse(data)

    def validate(self, data: Dict[str, Any]) -> tuple:
        """
        验证流程定义

        Args:
            data: 流程数据

        Returns:
            (is_valid, errors)
        """
        errors = []

        # 检查必需字段
        if not data.get("name"):
            errors.append("流程名称不能为空")

        if not data.get("steps"):
            errors.append("流程至少需要一个步骤")

        # 验证步骤
        step_ids = set()
        for i, step in enumerate(data.get("steps", [])):
            # 检查 ID 唯一性
            step_id = step.get("id", f"step_{i}")
            if step_id in step_ids:
                errors.append(f"步骤 ID 重复: {step_id}")
            step_ids.add(step_id)

            # 验证步骤类型
            step_type = step.get("type")
            if step_type not in self.step_type_map:
                errors.append(f"未知步骤类型: {step_type}")

        return len(errors) == 0, errors


class FlowValidator:
    """流程验证器"""

    @staticmethod
    def validate_steps(steps: List[Dict[str, Any]]) -> List[str]:
        """验证步骤定义"""
        errors = []

        for i, step in enumerate(steps):
            step_id = step.get("id", f"step_{i}")

            # 检查必需字段
            if not step.get("id"):
                errors.append(f"步骤 {i}: 缺少 ID")

            if not step.get("name"):
                errors.append(f"步骤 {step_id}: 缺少名称")

            # 验证步骤类型特定字段
            step_type = step.get("type")

            if step_type == "action":
                if not step.get("tool"):
                    errors.append(f"步骤 {step_id}: action 类型需要 tool 字段")

            elif step_type == "condition":
                if not step.get("condition"):
                    errors.append(f"步骤 {step_id}: condition 类型需要 condition 字段")

            elif step_type == "loop":
                if not step.get("condition") and not step.get("items"):
                    errors.append(f"步骤 {step_id}: loop 类型需要 condition 或 items 字段")

        return errors

    @staticmethod
    def validate_variables(variables: List[Dict[str, Any]]) -> List[str]:
        """验证变量定义"""
        errors = []
        names = set()

        for i, var in enumerate(variables):
            var_name = var.get("name")

            if not var_name:
                errors.append(f"变量 {i}: 缺少名称")
                continue

            if not var_name.isidentifier():
                errors.append(f"变量 {var_name}: 无效的标识符名称")

            if var_name in names:
                errors.append(f"变量 {var_name}: 名称重复")

            names.add(var_name)

        return errors
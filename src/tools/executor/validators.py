"""
参数验证策略模块

提供参数验证器接口和默认实现。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from src.tools.base import Tool, ToolParameters


# ========== 验证结果 ==========

@dataclass
class ValidationResult:
    """参数验证结果数据类"""
    valid: bool
    error: List[str] = field(default_factory=list)


# ========== 验证器接口 ==========

class IParamValidator(ABC):
    """
    参数验证器接口

    定义工具参数验证的标准接口。
    """

    @abstractmethod
    async def validate(self, tool: Tool, params: dict) -> ValidationResult:
        """
        验证工具参数

        Args:
            tool: 工具实例
            params: 待验证的参数字典

        Returns:
            ValidationResult: 验证结果
        """
        pass


# ========== 默认验证器 ==========

class DefaultValidator(IParamValidator):
    """
    默认参数验证器

    使用 pydantic 的 params_type 进行基础验证，
    并调用工具的 validate_param 方法进行自定义验证。
    """

    async def validate(self, tool: Tool, params: dict) -> ValidationResult:
        """
        验证工具参数

        Args:
            tool: 工具实例
            params: 待验证的参数字典

        Returns:
            ValidationResult: 验证结果
        """
        errors: List[str] = []

        # 1. 使用 pydantic 的 params_type 进行基础验证
        params_type = tool._get_params_type()

        # 检查是否是真正的类型
        if not isinstance(params_type, type):
            # 如果无法获取实际类型，直接验证通过
            # 假设 params 已经是正确类型的实例
            pass
        else:
            # 检查是否是继承自 ToolParameters 或 BaseModel 的类型
            try:
                from pydantic import BaseModel

                if issubclass(params_type, ToolParameters) or issubclass(params_type, BaseModel):
                    # 使用 pydantic 模型验证参数
                    try:
                        if hasattr(params_type, 'model_validate'):
                            params_type.model_validate(params)
                        else:
                            params_type.parse_obj(params)
                    except Exception as e:
                        errors.append(f"参数类型验证失败: {str(e)}")
            except (TypeError, ImportError):
                pass

        # 2. 调用工具的 validate_param 方法进行自定义验证（如果存在）
        if hasattr(tool, 'validate_param'):
            try:
                custom_result = await tool.validate_param(params)
                # 如果自定义验证返回 ValidationResult 类型，合并错误
                if custom_result and hasattr(custom_result, 'errors'):
                    if custom_result.errors:
                        errors.extend(custom_result.errors)
                # 如果返回的是布尔值且为 False，说明验证失败
                elif custom_result and isinstance(custom_result, bool) and not custom_result:
                    errors.append("自定义验证失败")
            except Exception as e:
                # 自定义验证方法抛出异常，记录但不影响主要验证流程
                errors.append(f"自定义验证异常: {str(e)}")

        # 返回验证结果
        return ValidationResult(
            valid=len(errors) == 0,
            error=errors
        )


__all__ = [
    "IParamValidator",
    "DefaultValidator",
    "ValidationResult",
]

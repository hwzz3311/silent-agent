"""
统一业务工具执行器

提供业务工具的统一定义和执行逻辑。
使用 BusinessToolRegistry 作为单一真相来源，替代硬编码映射。
"""

import asyncio
import logging
from typing import Any, Dict
from src.core.result import Result
from src.tools.domain.registry import BusinessToolRegistry
from src.tools.base import ExecutionContext
from pydantic import BaseModel

logger = logging.getLogger(__name__)


import warnings


class BusinessToolExecutor:
    """
    统一业务工具执行器（已废弃）

    请直接使用 HybridClient._execute_business_tool() 或
    BusinessToolRegistry.create_instance() + tool.execute()

    使用 BusinessToolRegistry 作为单一真相来源，替代硬编码映射。
    自动利用 @business_tool 装饰器的注册功能。

    Deprecated: 2026-03-06
    """

    @staticmethod
    def execute(name: str, params: Dict[str, Any] = None, context: Any = None) -> Dict[str, Any]:
        """Deprecated: 请使用 HybridClient._execute_business_tool()"""
        """
        执行业务工具

        通过 BusinessToolRegistry 查找并执行工具。

        Args:
            name: 工具名称（如 "xhs_check_login_status"）
            params: 工具参数字典
            context: 执行上下文（可为 None）

        Returns:
            执行结果字典

        Raises:
            ValueError: 工具不存在或未注册
            ConnectionError: 工具执行失败
        """
        params = params or {}

        # 1. 从注册表查找工具
        tool = BusinessToolRegistry.get(name)
        if not tool:
            available = BusinessToolRegistry.list_all()
            raise ValueError(f"未知业务工具: {name}，可用工具: {available[:5]}...")

        # 2. 确保 context 是 ExecutionContext 类型
        if context is None:
            context = ExecutionContext()
        elif not isinstance(context, ExecutionContext):
            # 如果是其他类型对象，确保有 secret_key 属性
            if not hasattr(context, 'secret_key'):
                context.secret_key = getattr(context, 'secret_key', None)

        # 3. 创建工具实例并执行
        try:
            # 从注册表创建新实例（确保干净状态）
            tool_instance = BusinessToolRegistry.create_instance(name)
            if not tool_instance:
                raise ValueError(f"无法创建工具实例: {name}")

            # 获取参数类型并验证
            param_type = getattr(tool_instance.__class__, '__parameter_type__', None)
            if param_type and issubclass(param_type, BaseModel):
                # 使用 pydantic 模型验证参数
                validated_params = param_type(**params)
            else:
                validated_params = params

            # 4. 异步执行工具
            result = tool_instance.execute(validated_params, context)

            # 如果是 coroutine，需要 await
            if asyncio.iscoroutine(result):
                result = asyncio.get_event_loop().run_until_complete(result)

            # 5. 自动转换 Result 对象为标准格式
            return BusinessToolExecutor._convert_result(result)

        except ValueError:
            # 参数验证错误直接抛出
            raise
        except Exception as e:
            logger.exception(f"工具执行失败: {name}")
            raise ConnectionError(f"业务工具执行失败: {e}")

    @staticmethod
    def _convert_result(result: Any) -> Dict[str, Any]:
        """将 Result 对象转换为标准格式"""
        from pydantic import BaseModel

        if not isinstance(result, Result):
            if isinstance(result, BaseModel):
                return {
                    "success": result.success,
                    "data": result.model_dump(),
                    "error": None
                }
            return result

        return {
            "success": result.success,
            "data": result.data,
            "error": str(result.error) if result.error else None
        }


__all__ = ["BusinessToolExecutor"]

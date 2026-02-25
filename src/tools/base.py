"""
工具抽象基类模块

提供 Tool 抽象基类，用于定义工具的标准化接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar, Optional, Dict, List
from pydantic import BaseModel, Field
import time

from src.core.result import Result, ResultMeta, Error, ErrorCode


# ========== 类型变量 ==========

TParams = TypeVar('TParams', bound=BaseModel)
TResult = TypeVar('TResult')


# ========== 参数定义 ==========

class ToolParameters(BaseModel):
    """工具参数基类"""
    class Config:
        extra = "forbid"  # 禁止额外字段

    def model_dump_strict(self) -> dict:
        """严格模式导出（只包含定义的字段）"""
        # Pydantic v2+ uses model_dump, v1 uses dict
        if hasattr(self, 'model_dump'):
            return self.model_dump(exclude_none=True, exclude_unset=True)
        else:
            return self.dict(exclude_none=True, exclude_unset=True)


class ValidationResult(BaseModel):
    """参数验证结果"""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ========== 执行上下文 ==========

@dataclass
class ExecutionContext:
    """
    执行上下文

    Attributes:
        tab_id: 标签页 ID
        world: 执行世界 (MAIN/ISOLATED)
        variables: 变量作用域链
        timeout: 执行超时时间（毫秒）
        retry_count: 重试次数
        retry_delay: 重试间隔（毫秒）
        client: 已连接的 SilentAgentClient 实例
    """
    tab_id: Optional[int] = None
    world: str = "MAIN"
    variables: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30000
    retry_count: int = 1
    retry_delay: int = 1000
    client: Any = None

    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)

    def set_variable(self, name: str, value: Any) -> None:
        """设置变量"""
        self.variables[name] = value

    def push_scope(self, variables: Dict[str, Any]) -> None:
        """推入新的变量作用域"""
        self.variables = {**self.variables, **variables}

    def pop_scope(self) -> Dict[str, Any]:
        """弹出变量作用域"""
        # 简化实现，实际应该维护作用域栈
        return self.variables

    @property
    def is_main_world(self) -> bool:
        """是否是 MAIN 世界"""
        return self.world == "MAIN"


# ========== 工具元信息 ==========

class ToolInfo(BaseModel):
    """工具元信息"""
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "general"
    tags: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Dict[str, Any] = Field(default_factory=dict)
    examples: List[str] = Field(default_factory=list)

    @classmethod
    def from_tool(cls, tool: 'Tool') -> 'ToolInfo':
        """从 Tool 实例创建"""
        return cls(
            name=tool.name,
            description=tool.description,
            version=tool.version,
            category=tool.category,
            tags=tool.tags,
        )


# ========== 工具执行结果 ==========

class ToolExecutionLog(BaseModel):
    """工具执行日志"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    success: bool
    duration_ms: int
    error: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


# ========== 工具抽象基类 ==========

class Tool(ABC, Generic[TParams, TResult]):
    """
    工具抽象基类

    所有工具都必须继承此类并实现以下方法：
    - execute(): 执行工具逻辑
    - validate_params(): 验证参数（可选）
    - get_info(): 返回工具元信息（可选）
    """

    # 工具名称（子类必须覆盖）
    name: str = "tool"

    # 工具描述（子类必须覆盖）
    description: str = "A tool"

    # 工具版本
    version: str = "1.0.0"

    # 工具分类
    category: str = "general"

    # 工具标签
    tags: List[str] = []

    # 是否是内置工具
    is_builtin: bool = False

    # ========== 抽象方法 ==========

    @abstractmethod
    async def execute(
        self,
        params: TParams,
        context: ExecutionContext
    ) -> Result[TResult]:
        """
        执行工具逻辑

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[TResult]: 执行结果
        """
        ...

    # ========== 可选覆盖方法 ==========

    def get_parameters_schema(self) -> Dict[str, Any]:
        """
        获取参数 JSON Schema

        Returns:
            JSON Schema 字典
        """
        params_type = self._get_params_type()

        # 检查是否是真正的类型（不是 TypeVar）
        if params_type is TParams or not isinstance(params_type, type):
            return {"type": "object", "properties": {}}

        # Pydantic v2+ uses model_json_schema, v1 uses schema_of
        try:
            from pydantic import model_json_schema
            return model_json_schema(params_type)
        except ImportError:
            # Fallback for Pydantic v1
            from pydantic import schema_of
            return schema_of(params_type)

    def get_returns_schema(self) -> Dict[str, Any]:
        """
        获取返回值 JSON Schema

        Returns:
            JSON Schema 字典
        """
        # 简化实现，假设返回类型是简单类型或 Result
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {"description": "Result data"}
            }
        }

    def get_info(self) -> ToolInfo:
        """
        获取工具元信息

        Returns:
            ToolInfo 对象
        """
        return ToolInfo.from_tool(self)

    def _get_params_type(self) -> type:
        """
        获取参数类型

        Returns:
            参数类型
        """
        # 优先使用 __parameters_type__ 属性
        params_type = getattr(self, '__parameters_type__', None)
        if params_type:
            return params_type

        # 尝试从泛型基类获取类型参数
        import typing
        orig_bases = getattr(self.__class__, '__orig_bases__', None)
        if orig_bases:
            for base in orig_bases:
                if hasattr(base, '__args__'):
                    args = getattr(base, '__args__', None)
                    if args and len(args) >= 1:
                        # Tool[TParams, TResult]:
                        #   args[0] = TParams (参数类型), args[1] = TResult (结果类型)
                        # BusinessTool[TSite, TParams]:
                        #   args[0] = TSite (Site类型), args[1] = TParams (参数类型)

                        # 遍历 args，找到继承自 ToolParameters 或 BaseModel 的类型
                        for arg in args:
                            # 跳过 TypeVar
                            if arg is TParams or arg is TResult:
                                continue
                            # 检查是否是实际的类（非 TypeVar）
                            if isinstance(arg, type):
                                try:
                                    # 检查是否继承自 ToolParameters 或 BaseModel
                                    # 参数类型应该是 Pydantic 模型
                                    from src.tools.base import ToolParameters
                                    is_params = (
                                        issubclass(arg, ToolParameters) or
                                        issubclass(arg, BaseModel)
                                    )
                                    if is_params:
                                        return arg
                                except TypeError:
                                    # issubclass 需要实际类型，不是 TypeVar
                                    continue

        # Fallback: 使用 TParams (注意：这可能是 TypeVar)
        return TParams

    async def validate_params(self, params: TParams) -> ValidationResult:
        """
        验证参数

        Args:
            params: 待验证的参数

        Returns:
            ValidationResult: 验证结果
        """
        try:
            params_type = self._get_params_type()

            # 检查是否是真正的类型（不是 TypeVar）
            if params_type is TParams or not isinstance(params_type, type):
                # 如果无法获取实际类型，直接验证通过
                # 假设 params 已经是正确类型的实例
                return ValidationResult(valid=True)

            # Pydantic v2+ uses model_validate, v1 uses parse_obj
            if hasattr(params_type, 'model_validate'):
                validated = params_type.model_validate(params)
            else:
                validated = params_type.parse_obj(params)
            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[str(e)]
            )

    async def execute_with_validation(
        self,
        params: TParams,
        context: ExecutionContext
    ) -> Result[TResult]:
        """
        带验证的执行

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[TResult]: 执行结果
        """
        # 验证参数
        validation = await self.validate_params(params)
        if not validation.valid:
            return Result.fail(
                Error.validation(
                    message="参数验证失败",
                    details={"errors": validation.errors}
                )
            )

        # 执行
        return await self.execute(params, context)

    async def execute_with_retry(
        self,
        params: TParams,
        context: ExecutionContext
    ) -> Result[TResult]:
        """
        带重试的执行

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[TResult]: 执行结果
        """
        last_error = None

        for attempt in range(1, context.retry_count + 1):
            try:
                result = await self.execute_with_validation(
                    params,
                    context
                )

                if result.success:
                    # 添加尝试次数到元数据
                    if result.meta:
                        result.meta.attempt = attempt
                    return result

                # 如果错误不可恢复，直接返回
                if result.error and not result.error.recoverable:
                    return result

                last_error = result.error

            except Exception as e:
                last_error = Error.from_exception(e)

            # 等待后重试
            if attempt < context.retry_count:
                await self._sleep(context.retry_delay)

        # 所有尝试都失败
        return Result.fail(
            last_error or Error.unknown("执行失败"),
            meta=ResultMeta(
                tool_name=self.name,
                duration_ms=context.retry_count * context.retry_delay,
                attempt=context.retry_count,
            )
        )

    async def _sleep(self, ms: int) -> None:
        """异步睡眠"""
        import asyncio
        await asyncio.sleep(ms / 1000)

    # ========== 工具方法 ==========

    def ok(self, data: TResult = None, meta: ResultMeta = None) -> Result[TResult]:
        """创建成功结果"""
        return Result.ok(data, meta)

    def fail(
        self,
        message: str = "执行失败",
        code: ErrorCode = ErrorCode.EXECUTION_FAILED,
        recoverable: bool = False,
        details: dict = None
    ) -> Result[TResult]:
        """创建失败结果"""
        return Result.fail(
            Error(
                code=code.value,
                message=message,
                recoverable=recoverable,
                details=details,
            )
        )

    def error_from_exception(
        self,
        exc: Exception,
        code: ErrorCode = None,
        recoverable: bool = False
    ) -> Result[TResult]:
        """从异常创建失败结果"""
        return Result.fail(Error.from_exception(exc, code, recoverable))


# ========== 工具工厂 ==========

class ToolFactory:
    """工具工厂"""

    _tools: Dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        """注册工具"""
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> Optional[Tool]:
        """获取工具"""
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[str]:
        """列出所有工具"""
        return list(cls._tools.keys())

    @classmethod
    def clear(cls) -> None:
        """清空所有工具"""
        cls._tools.clear()

    @classmethod
    def create_from_params(cls, name: str, params_dict: dict) -> Optional[Result]:
        """
        根据参数字典创建参数对象

        Args:
            name: 工具名称
            params_dict: 参数字典

        Returns:
            Result，包含参数对象
        """
        tool = cls.get(name)
        if not tool:
            return Result.fail(
                Error.tool_not_found(name),
                meta=ResultMeta(tool_name=name, duration_ms=0)
            )

        try:
            # 查找 ToolParams 类型并创建实例
            params_type = getattr(tool, '__parameters_type__', None)
            if params_type:
                params = params_type(**params_dict)
            else:
                # 使用字典作为参数
                params = params_dict
            return Result.ok(params)
        except Exception as e:
            return Result.fail(
                Error.validation(
                    message=f"参数创建失败: {e}",
                    details={"params": params_dict}
                ),
                meta=ResultMeta(tool_name=name, duration_ms=0)
            )


# ========== 便捷函数 ==========

def tool(name: str, description: str = "", category: str = "general",
         version: str = "1.0.0", tags: list = None):
    """
    工具装饰器

    Args:
        name: 工具名称
        description: 工具描述
        category: 工具分类
        version: 工具版本
        tags: 工具标签列表

    Returns:
        装饰器函数
    """
    def decorator(cls):
        cls.name = name
        cls.description = description
        cls.category = category
        cls.version = version
        cls.tags = tags or []
        return cls
    return decorator


__all__ = [
    "Tool",
    "ToolInfo",
    "ToolParameters",
    "ValidationResult",
    "ExecutionContext",
    "ToolExecutionLog",
    "ToolFactory",
    "tool",
]
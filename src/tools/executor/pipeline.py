"""
执行管道模块

提供工具执行的管道化处理，包括参数验证、前置检查、后置处理和重试策略。
"""

from typing import Any, Optional
import asyncio
import time
import logging

from src.tools.base import Tool, ToolParameters, ExecutionContext
from src.core.result import Result, ResultMeta, Error, ErrorCode

logger = logging.getLogger(__name__)


# ========== 默认实现 ==========

class DefaultParamValidator:
    """默认参数验证器"""

    async def validate(self, tool: Tool, params: Any) -> Result:
        """使用工具内置的 validate_param 方法验证参数"""
        try:
            # 检查工具是否有 validate_param 方法
            if hasattr(tool, 'validate_param') and callable(getattr(tool, 'validate_param')):
                validation = await tool.validate_param(params)
                if not validation.valid:
                    return Result.fail(
                        Error.validation(
                            message="参数验证失败",
                            details={"errors": validation.errors, "warnings": validation.warnings}
                        )
                    )
            # 如果没有 validate_param 方法，直接通过验证
            return Result.ok(data=params)
        except Exception as e:
            return Result.fail(Error.from_exception(e, ErrorCode.VALIDATION_ERROR, recoverable=True))


class DefaultPreCheck:
    """默认前置检查器（空实现）"""

    async def check(self, tool: Tool, params: Any, context: ExecutionContext) -> Result:
        """默认前置检查直接通过"""
        return Result.ok()


class DefaultPostProcessor:
    """默认后置处理器（空实现）"""

    async def process(
        self,
        tool: Tool,
        params: Any,
        context: ExecutionContext,
        result: Result
    ) -> Result:
        """默认后置处理直接返回原结果"""
        return result


class DefaultRetryStrategy:
    """默认重试策略"""

    def __init__(self, base_delay: float = 1.0, max_delay: float = 30.0, exponential: bool = True):
        """
        初始化重试策略

        Args:
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            exponential: 是否使用指数退避
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential = exponential

    def should_retry(self, result: Result, attempt: int, max_attempts: int) -> bool:
        """根据错误是否可恢复决定是否重试"""
        if result.success:
            return False
        if attempt >= max_attempts:
            return False
        # 检查错误是否可恢复
        if result.error and result.error.recoverable:
            return True
        return False

    async def get_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        if self.exponential:
            delay = self.base_delay * (2 ** (attempt - 1))
        else:
            delay = self.base_delay
        return min(delay, self.max_delay)


# ========== 执行管道 ==========

class ExecutionPipeline:
    """
    执行管道

    提供完整的工具执行流程：参数验证 → 前置检查 → 核心执行 → 后置处理

    支持可插拔的参数验证器、前置检查器、后置处理器和重试策略。

    Attributes:
        param_validator: 参数验证器
        pre_check: 前置检查器
        post_processor: 后置处理器
        retry_strategy: 重试策略
    """

    def __init__(
        self,
        param_validator: Optional[DefaultParamValidator] = None,
        pre_check: Optional[DefaultPreCheck] = None,
        post_processor: Optional[DefaultPostProcessor] = None,
        retry_strategy: Optional[DefaultRetryStrategy] = None
    ):
        """
        初始化执行管道

        Args:
            param_validator: 参数验证器（默认 DefaultParamValidator）
            pre_check: 前置检查器（默认 DefaultPreCheck）
            post_processor: 后置处理器（默认 DefaultPostProcessor）
            retry_strategy: 重试策略（默认 DefaultRetryStrategy）
        """
        self.param_validator = param_validator or DefaultParamValidator()
        self.pre_check = pre_check or DefaultPreCheck()
        self.post_processor = post_processor or DefaultPostProcessor()
        self.retry_strategy = retry_strategy or DefaultRetryStrategy()

    async def execute(
        self,
        tool: Tool,
        params: Any,
        context: ExecutionContext
    ) -> Result:
        """
        执行完整流程

        执行流程：参数验证 → 前置检查 → 核心执行 → 后置处理
        包含重试逻辑和完整的错误处理。

        Args:
            tool: 工具实例
            params: 工具参数
            context: 执行上下文

        Returns:
            Result: 执行结果
        """
        max_attempts = getattr(context, 'retry_count', 1) or 1
        last_result = None

        for attempt in range(1, max_attempts + 1):
            # 记录开始时间
            start_time = time.time()

            try:
                # 执行单次尝试
                result = await self._execute_single_attempt(
                    tool, params, context, attempt
                )

                # 记录执行时间
                duration_ms = int((time.time() - start_time) * 1000)
                if result.meta:
                    result.meta.duration_ms = duration_ms
                    result.meta.attempt = attempt

                # 检查是否成功
                if result.success:
                    return result

                # 记录失败结果
                last_result = result

                # 判断是否需要重试
                if not self.retry_strategy.should_retry(result, attempt, max_attempts):
                    return result

                # 获取延迟时间并等待
                delay = await self.retry_strategy.get_delay(attempt)
                logger.info(
                    f"工具 {tool.name} 第 {attempt} 次执行失败，准备重试，延迟 {delay}s"
                )
                await asyncio.sleep(delay)

            except Exception as e:
                # 捕获执行过程中的异常
                duration_ms = int((time.time() - start_time) * 1000)
                error = Error.from_exception(e, recoverable=True)

                last_result = Result.fail(
                    error=error,
                    meta=ResultMeta(
                        tool_name=tool.name,
                        duration_ms=duration_ms,
                        attempt=attempt
                    )
                )

                # 判断是否需要重试
                if not self.retry_strategy.should_retry(last_result, attempt, max_attempts):
                    return last_result

                # 获取延迟时间并等待
                delay = await self.retry_strategy.get_delay(attempt)
                logger.exception(f"工具 {tool.name} 第 {attempt} 次执行异常，准备重试")
                await asyncio.sleep(delay)

        # 所有尝试都失败
        if last_result:
            return last_result

        return Result.fail(
            Error.unknown("工具执行失败"),
            meta=ResultMeta(tool_name=tool.name, duration_ms=0, attempt=max_attempts)
        )

    async def _execute_single_attempt(
        self,
        tool: Tool,
        params: Any,
        context: ExecutionContext,
        attempt: int
    ) -> Result:
        """
        执行单次尝试

        执行流程：参数验证 → 前置检查 → 核心执行 → 后置处理

        Args:
            tool: 工具实例
            params: 工具参数
            context: 执行上下文
            attempt: 当前尝试次数

        Returns:
            Result: 执行结果
        """
        # ========== 1. 参数验证 ==========
        validation_result = await self.param_validator.validate(tool, params)
        if not validation_result.success:
            return Result.fail(
                error=validation_result.error,
                meta=ResultMeta(
                    tool_name=tool.name,
                    duration_ms=0,
                    attempt=attempt
                )
            )

        # 获取验证后的参数
        validated_params = validation_result.data if validation_result.data is not None else params

        # ========== 2. 前置检查 ==========
        pre_check_result = await self.pre_check.check(tool, validated_params, context)
        if not pre_check_result.success:
            return Result.fail(
                error=pre_check_result.error,
                meta=ResultMeta(
                    tool_name=tool.name,
                    duration_ms=0,
                    attempt=attempt
                )
            )

        # ========== 3. 核心执行 ==========
        try:
            result = await tool.execute(validated_params, context)
        except Exception as e:
            # 转换异常为错误结果
            result = Result.fail(
                error=Error.from_exception(e, recoverable=True),
                meta=ResultMeta(tool_name=tool.name, duration_ms=0, attempt=attempt)
            )

        # ========== 4. 后置处理 ==========
        post_result = await self.post_processor.process(
            tool, validated_params, context, result
        )

        return post_result


# ========== 便捷工厂函数 ==========

def create_default_pipeline() -> ExecutionPipeline:
    """
    创建默认执行管道

    Returns:
        ExecutionPipeline: 默认执行管道实例
    """
    return ExecutionPipeline()


__all__ = [
    # 默认实现
    "DefaultParamValidator",
    "DefaultPreCheck",
    "DefaultPostProcessor",
    "DefaultRetryStrategy",
    # 执行管道
    "ExecutionPipeline",
    # 便捷函数
    "create_default_pipeline",
]

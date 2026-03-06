"""
重试策略模块

提供工具执行失败时的重试策略接口和实现。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Callable, Awaitable, TypeVar

from src.core.result import Error, Result

T = TypeVar('T')

logger = logging.getLogger(__name__)


class IRetryStrategy(ABC):
    """
    重试策略接口

    定义工具执行失败时的重试行为。
    """

    @abstractmethod
    async def execute(self, func: Callable[[], Awaitable[Result[T]]]) -> Result[T]:
        """
        执行带重试策略的异步函数

        Args:
            func: 异步函数，返回 Result

        Returns:
            Result: 执行结果（成功或失败）
        """
        pass


class NoRetryStrategy(IRetryStrategy):
    """
    不重试策略

    执行一次，直接返回结果，不进行任何重试。
    """

    async def execute(self, func: Callable[[], Awaitable[Result[T]]]) -> Result[T]:
        """执行一次，不重试"""
        return await func()


class ExponentialBackoffRetry(IRetryStrategy):
    """
    指数退避重试策略

    执行失败后使用指数退避算法进行重试。
    每次重试的等待时间 = base_delay * (2 ^ attempt)

    Attributes:
        max_attempts: 最大重试次数（包含首次尝试）
        base_delay: 基础延迟时间（秒）
    """

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        """
        初始化指数退避重试策略

        Args:
            max_attempts: 最大重试次数，默认为 3
            base_delay: 基础延迟时间（秒），默认为 1.0
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if base_delay <= 0:
            raise ValueError("base_delay must be > 0")

        self.max_attempts = max_attempts
        self.base_delay = base_delay

    async def execute(self, func: Callable[[], Awaitable[Result[T]]]) -> Result[T]:
        """
        使用指数退避算法执行重试

        执行流程:
        1. 首次尝试执行函数
        2. 如果成功，返回结果
        3. 如果失败且可恢复（error.recoverable），等待后重试
        4. 最多重试 max_attempt 次
        """
        last_result: Result[T] = None
        attempt = 0

        while attempt < self.max_attempt:
            attempt += 1

            try:
                result = await func()
                last_result = result

                if result.success:
                    # 成功，更新尝试次数到 meta
                    if result.meta:
                        result.meta.attempt = attempt
                    logger.debug(f"执行成功 (attempt {attempt}/{self.max_attempt})")
                    return result

                # 失败，检查是否可恢复
                if result.error and result.error.recoverable:
                    logger.warning(
                        f"执行失败 (attempt {attempt}/{self.max_attempt}): "
                        f"{result.error.message}，将重试"
                    )

                    # 如果不是最后一次尝试，等待后重试
                    if attempt < self.max_attempt:
                        delay = self.base_delay * (2 ** (attempt - 1))
                        logger.debug(f"等待 {delay:.2f}秒后重试...")
                        await asyncio.sleep(delay)
                        continue
                else:
                    # 不可恢复的错误，直接返回
                    logger.error(
                        f"执行失败且不可恢复 (attempt {attempt}/{self.max_attempt}): "
                        f"{result.error.message}"
                    )
                    return result

            except Exception as e:
                logger.exception(f"执行异常 (attempt {attempt}/{self.max_attempt}): {e}")

                # 记录异常作为失败结果
                last_result = Result.from_execution(
                    success=False,
                    error=Error.from_exception(e, recoverable=True),
                    tool_name="unknown",
                    duration_ms=0,
                )

                # 如果不是最后一次尝试，等待后重试
                if attempt < self.max_attempt:
                    delay = self.base_delay * (2 ** (attempt - 1))
                    logger.debug(f"等待 {delay:.2f}秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    break

        # 所有尝试都失败
        if last_result:
            logger.error(f"重试 {self.max_attempt} 次后仍失败")
            return last_result

        # 兜底（理论上不会到达）
        return Result.fail(
            Error.unknown("重试策略执行失败，未知原因"),
        )


__all__ = [
    "IRetryStrategy",
    "NoRetryStrategy",
    "ExponentialBackoffRetry",
]

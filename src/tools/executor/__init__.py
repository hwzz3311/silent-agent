"""
执行器模块

提供工具执行的管道化处理、参数验证、重试策略和前置检查。

核心组件:
- ExecutionPipeline: 执行管道
- IParamValidator/DefaultValidator: 参数验证
- IRetryStrategy/NoRetryStrategy/ExponentialBackoffRetry: 重试策略
- IPreCheck/DefaultPreCheck/LoginRequiredCheck: 前置检查

依赖注入支持:
- get_default_pipeline(): 获取默认管道
- set_pipeline(): 注入自定义管道
- reset_pipeline(): 重置为默认管道
- create_pipeline(): 创建带自定义策略的执行管道
"""

from typing import Optional

# 从 pipeline 模块导入
from src.tools.executor.pipeline import (
    ExecutionPipeline,
    IParamValidator,
    IPreCheck,
    IPostProcessor,
    IRetryStrategy,
    DefaultParamValidator,
    DefaultPreCheck,
    DefaultPostProcessor,
    DefaultRetryStrategy,
    create_default_pipeline,
)

# 从 validators 模块导入
from src.tools.executor.validators import (
    IParamValidator as IParamValidatorFromValidators,
    DefaultValidator,
    ValidationResult,
)

# 从 retry_strategies 模块导入
from src.tools.executor.retry_strategies import (
    IRetryStrategy as IRetryStrategyFromRetry,
    NoRetryStrategy,
    ExponentialBackoffRetry,
)

# 从 pre_check 模块导入
from src.tools.executor.pre_check import (
    IPreCheck as IPreCheckFromPreCheck,
    DefaultPreCheck as DefaultPreCheckFromPreCheck,
    LoginRequiredCheck,
)


# ========== 依赖注入支持 ==========

# 模块级默认管道变量
_default_pipeline: Optional[ExecutionPipeline] = None


def get_default_pipeline() -> ExecutionPipeline:
    """
    获取默认执行管道

    如果已经通过 set_pipeline 注入了自定义管道，返回该管道。
    否则创建并返回默认管道。

    Returns:
        ExecutionPipeline: 默认或自定义执行管道
    """
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = create_default_pipeline()
    return _default_pipeline


def set_pipeline(pipeline: ExecutionPipeline) -> None:
    """
    注入自定义执行管道

    用于测试或需要自定义执行行为的场景。

    Args:
        pipeline: 自定义的执行管道
    """
    global _default_pipeline
    _default_pipeline = pipeline


def reset_pipeline() -> None:
    """
    重置为默认执行管道

    清除自定义管道，恢复使用默认管道。
    """
    global _default_pipeline
    _default_pipeline = None


# ========== 便捷工厂函数 ==========

def create_pipeline(
    param_validator: Optional[IParamValidator] = None,
    pre_check: Optional[IPreCheck] = None,
    post_processor: Optional[IPostProcessor] = None,
    retry_strategy: Optional[IRetryStrategy] = None,
) -> ExecutionPipeline:
    """
    创建带自定义策略的执行管道

    便捷工厂函数，允许仅传入需要自定义的组件，其他使用默认实现。

    Args:
        param_validator: 参数验证器（默认 DefaultParamValidator）
        pre_check: 前置检查器（默认 DefaultPreCheck）
        post_processor: 后置处理器（默认 DefaultPostProcessor）
        retry_strategy: 重试策略（默认 DefaultRetryStrategy）

    Returns:
        ExecutionPipeline: 配置好的执行管道

    Example:
        # 使用默认管道
        pipeline = create_pipeline()

        # 使用自定义重试策略
        pipeline = create_pipeline(
            retry_strategy=ExponentialBackoffRetry(max_attempt=5, base_delay=2.0)
        )

        # 使用自定义前置检查（登录检查）
        pipeline = create_pipeline(
            pre_check=LoginRequiredCheck()
        )
    """
    return ExecutionPipeline(
        param_validator=param_validator,
        pre_check=pre_check,
        post_processor=post_processor,
        retry_strategy=retry_strategy,
    )


# ========== 模块导出 ==========

__all__ = [
    # 管道核心
    "ExecutionPipeline",
    "create_default_pipeline",
    "create_pipeline",
    # 参数验证
    "IParamValidator",
    "DefaultValidator",
    "ValidationResult",
    # 重试策略
    "IRetryStrategy",
    "NoRetryStrategy",
    "ExponentialBackoffRetry",
    # 前置检查
    "IPreCheck",
    "DefaultPreCheck",
    "LoginRequiredCheck",
    # 后置处理
    "IPostProcessor",
    "DefaultPostProcessor",
    # 依赖注入
    "get_default_pipeline",
    "set_pipeline",
    "reset_pipeline",
]

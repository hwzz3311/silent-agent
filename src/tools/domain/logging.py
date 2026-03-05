"""
业务日志记录器

提供业务操作的结构化日志记录功能。
"""

import functools
import logging
import time
from typing import TYPE_CHECKING, Callable, Any, Dict

if TYPE_CHECKING:
    pass

from .errors import BusinessException


# 默认的日志敏感字段列表
DEFAULT_SENSITIVE_FIELDS = [
    "password", "token", "secret", "key", "auth", "credential",
    "cookie", "session", "access_token", "refresh_token"
]


def mask_sensitive_data(data: str, fields: list = None) -> str:
    """
    对敏感数据进行脱敏处理

    Args:
        data: 原始数据
        fields: 敏感字段列表

    Returns:
        str: 脱敏后的数据
    """
    import re

    fields = fields or DEFAULT_SENSITIVE_FIELDS

    for field in fields:
        # 脱敏 key=value 格式的值
        escaped_field = field.replace('{', '{{').replace('}', '}}')
        pattern = rf'({escaped_field}["\']?\s*[:=]\s*["\']?)([^"\'&,\s}}]+)'
        data = re.sub(pattern, r'\1******', data, flags=re.IGNORECASE)

    return data


class BusinessLogger:
    """
    业务日志记录器

    功能:
    1. 结构化日志输出
    2. 自动包含站点和操作信息
    3. 错误上下文记录
    4. 性能监控

    Usage:
        logger = BusinessLogger("xiaohongshu", "check_login_status")
        logger.log_step("开始检查登录状态")
        # ... 业务逻辑
        logger.log_result(True, result_data)
    """

    def __init__(
        self,
        site_name: str,
        operation: str,
        logger: logging.Logger = None,
        sensitive_fields: list = None
    ):
        """
        初始化业务日志记录器

        Args:
            site_name: 网站名称
            operation: 操作名称
            logger: Python 日志记录器
            sensitive_fields: 敏感字段列表
        """
        self.site_name = site_name
        self.operation = operation
        self.logger = logger or logging.getLogger(__name__)
        self.sensitive_fields = sensitive_fields or DEFAULT_SENSITIVE_FIELDS
        self._start_time = None
        self._step_count = 0

    @property
    def context(self) -> Dict[str, str]:
        """获取日志上下文"""
        return {
            "site": self.site_name,
            "operation": self.operation,
        }

    def _log(
        self,
        level: int,
        message: str,
        extra: Dict[str, Any] = None,
        mask_data: bool = True
    ):
        """
        内部日志记录方法

        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外字段
            mask_data: 是否对数据进行脱敏
        """
        # 构建日志额外字段
        log_extra = {
            **self.context,
            "elapsed_ms": self._get_elapsed_ms() if self._start_time else None,
            "step": self._step_count,
        }

        if extra:
            log_extra.update(extra)

        # 对敏感数据进行脱敏
        if mask_data and "data" in log_extra:
            log_extra["data"] = mask_sensitive_data(
                str(log_extra["data"]),
                self.sensitive_fields
            )

        self.logger.log(level, message, extra=log_extra)

    def _get_elapsed_ms(self) -> int:
        """获取已过时间（毫秒）"""
        if self._start_time is None:
            return 0
        return int((time.time() - self._start_time) * 1000)

    # ========== 日志记录方法 ==========

    def log_step(self, step: str, **kwargs):
        """
        记录步骤

        Args:
            step: 步骤描述
            **kwargs: 额外字段
        """
        self._step_count += 1
        self._log(
            logging.INFO,
            f"[{self.operation}] 步骤 {self._step_count}: {step}",
            extra=kwargs
        )

    def log_substep(self, substep: str, **kwargs):
        """
        记录子步骤

        Args:
            substep: 子步骤描述
            **kwargs: 额外字段
        """
        self._log(
            logging.DEBUG,
            f"  - {substep}",
            extra=kwargs
        )

    def log_data(self, data_name: str, data_value: Any):
        """
        记录数据（自动脱敏）

        Args:
            data_name: 数据名称
            data_value: 数据值
        """
        self._log(
            logging.DEBUG,
            f"  数据 {data_name}: {str(data_value)[:100]}...",
            extra={"data_name": data_name}
        )

    def log_result(self, success: bool, result: Any = None, **kwargs):
        """
        记录结果

        Args:
            success: 是否成功
            result: 结果数据
            **kwargs: 额外字段
        """
        status = "成功" if success else "失败"
        level = logging.INFO if success else logging.WARNING

        message = f"[{self.operation}] {status}"
        if result is not None:
            message += f" - 结果: {str(result)[:100]}"

        self._log(
            level,
            message,
            extra={"success": success, "result": str(result)[:200] if result else None, **kwargs}
        )

    def log_error(self, error: Exception, **kwargs):
        """
        记录错误

        Args:
            error: 异常对象
            **kwargs: 额外字段
        """
        if isinstance(error, BusinessException):
            error_code = error.code.value if hasattr(error.code, 'value') else error.code
            error_message = error.to_exception_message()
        else:
            error_code = "UNKNOWN"
            error_message = str(error)

        self._log(
            logging.ERROR,
            f"[{self.operation}] 错误: {error_message}",
            extra={
                "error_code": error_code,
                "error_message": error_message,
                "is_recoverable": getattr(error, 'is_recoverable', True),
                **kwargs
            }
        )

    def log_warning(self, message: str, **kwargs):
        """
        记录警告

        Args:
            message: 警告消息
            **kwargs: 额外字段
        """
        self._log(logging.WARNING, f"[{self.operation}] 警告: {message}", extra=kwargs)

    def log_info(self, message: str, **kwargs):
        """
        记录信息

        Args:
            message: 消息
            **kwargs: 额外字段
        """
        self._log(logging.INFO, f"[{self.operation}] {message}", extra=kwargs)

    def log_debug(self, message: str, **kwargs):
        """
        记录调试信息

        Args:
            message: 消息
            **kwargs: 额外字段
        """
        self._log(logging.DEBUG, f"[{self.operation}] {message}", extra=kwargs)

    # ========== 性能监控 ==========

    def start_timer(self):
        """开始计时"""
        self._start_time = time.time()
        self._step_count = 0
        return self

    def stop_timer(self) -> int:
        """
        停止计时并返回耗时（毫秒）

        Returns:
            int: 耗时（毫秒）
        """
        elapsed = self._get_elapsed_ms()
        self._log(
            logging.INFO,
            f"[{self.operation}] 完成，耗时: {elapsed}ms",
            extra={"elapsed_ms": elapsed}
        )
        self._start_time = None
        return elapsed

    def log_duration(self, operation: str, duration_ms: int, **kwargs):
        """
        记录操作耗时

        Args:
            operation: 操作名称
            duration_ms: 耗时（毫秒）
            **kwargs: 额外字段
        """
        self._log(
            logging.INFO,
            f"操作 {operation} 完成，耗时: {duration_ms}ms",
            extra={"duration_ms": duration_ms, "operation": operation, **kwargs}
        )

    # ========== 上下文管理 ==========

    def bind(self, **kwargs) -> 'BusinessLogger':
        """
        绑定额外上下文

        Args:
            **kwargs: 额外上下文字段

        Returns:
            BusinessLogger: 新的日志记录器实例
        """
        new_logger = BusinessLogger(
            self.site_name,
            self.operation,
            self.logger,
            self.sensitive_fields
        )
        # 保留计时状态
        new_logger._start_time = self._start_time
        new_logger._step_count = self._step_count
        return new_logger


def log_operation(
    operation_name: str = None,
    log_args: bool = True,
    log_result: bool = True,
    log_duration: bool = True
) -> Callable:
    """
    业务操作日志装饰器

    自动记录:
    1. 操作开始
    2. 操作参数（可脱敏）
    3. 操作结果
    4. 操作耗时

    Args:
        operation_name: 操作名称（默认使用方法名）
        log_args: 是否记录参数
        log_result: 是否记录结果
        log_duration: 是否记录耗时

    Returns:
        装饰器函数

    Usage:
        @log_operation("check_login")
        async def check_login_status(params):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 获取操作名称
            op_name = operation_name or func.__name__

            # 获取 logger
            logger = BusinessLogger("unknown", op_name)

            # 记录开始
            logger.log_step("开始执行")

            if log_args and kwargs:
                logger.log_substep(f"参数: {list(kwargs.keys())}")

            # 执行函数
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)

                # 记录成功
                if log_result:
                    logger.log_result(True, result)

                return result

            except Exception as e:
                # 记录错误
                logger.log_error(e)
                raise

            finally:
                # 记录耗时
                if log_duration:
                    duration = int((time.time() - start_time) * 1000)
                    logger.log_duration(op_name, duration)

        return wrapper

    return decorator


class PerformanceLogger:
    """
    性能日志记录器

    用于记录操作的性能指标。
    """

    def __init__(self, logger: logging.Logger = None):
        """
        初始化性能日志记录器

        Args:
            logger: Python 日志记录器
        """
        self.logger = logger or logging.getLogger("performance")
        self.measurements: Dict[str, list] = {}

    def measure(self, operation: str) -> 'PerformanceContext':
        """
        开始测量操作性能

        Args:
            operation: 操作名称

        Returns:
            PerformanceContext: 性能测量上下文
        """
        return PerformanceContext(self, operation)

    def log_statistics(self, operation: str):
        """
        记录操作统计信息

        Args:
            operation: 操作名称
        """
        if operation not in self.measurements:
            return

        measurements = self.measurements[operation]
        if not measurements:
            return

        import statistics

        self.logger.info(
            f"性能统计 - {operation}: "
            f"次数={len(measurements)}, "
            f"平均={statistics.mean(measurements):.2f}ms, "
            f"最大={max(measurements):.2f}ms, "
            f"最小={min(measurements):.2f}ms"
        )


class PerformanceContext:
    """
    性能测量上下文

    Usage:
        with performance_logger.measure("operation_name"):
            # 执行操作
            pass
    """

    def __init__(self, logger: PerformanceLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (time.time() - self.start_time) * 1000
            if self.operation not in self.logger.measurements:
                self.logger.measurements[self.operation] = []
            self.logger.measurements[self.operation].append(duration)
        return False  # 不抑制异常

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (time.time() - self.start_time) * 1000
            if self.operation not in self.logger.measurements:
                self.logger.measurements[self.operation] = []
            self.logger.measurements[self.operation].append(duration)
        return False


def setup_business_logging(
    level: int = logging.INFO,
    format: str = None,
    log_file: str = None
) -> logging.Logger:
    """
    设置业务日志配置

    Args:
        level: 日志级别
        format: 日志格式
        log_file: 日志文件路径

    Returns:
        logging.Logger: 配置后的根日志记录器
    """
    # 默认格式
    default_format = (
        "%(asctime)s | %(levelname)-8s | "
        "%(site)s | %(operation)s | "
        "step=%(step)s | elapsed=%(elapsed_ms)sms | "
        "%(message)s"
    )

    formatter = logging.Formatter(format or default_format)

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 添加文件处理器（如果指定）
    if log_file:
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


__all__ = [
    "BusinessLogger",
    "log_operation",
    "PerformanceLogger",
    "PerformanceContext",
    "setup_business_logging",
    "mask_sensitive_data",
    "DEFAULT_SENSITIVE_FIELDS",
]
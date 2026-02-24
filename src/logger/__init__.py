"""
日志系统模块

提供完整的日志功能，包括配置、格式化、处理和执行日志记录。

主要组件:
- LogConfig: 日志配置
- Formatter: 日志格式化器
- Handler: 日志处理器
- ExecutionLogger: 执行日志记录器

使用示例:
```python
from logger import (
    LogConfig, LogLevel,
    FormatterFactory,
    HandlerFactory,
    ExecutionLogger, ExecutionLogManager,
    get_execution_logger,
)

# 配置日志
config = LogConfig.default()

# 创建格式化器
formatter = FormatterFactory.create("structured")

# 创建处理器
handler = HandlerFactory.create("file", filename="neurone.log")

# 获取执行日志记录器
logger = get_execution_logger()
logger.start()

# 记录日志
logger.info("开始执行流程")
logger.step_start("登录步骤", "browser.navigate")
# ... 执行步骤 ...
logger.step_end("登录步骤", result={"success": True})

logger.info("流程执行完成")
```

日志文件保存位置:
- 默认: ~/.neurone/logs/neurone_YYYYMMDD.log
"""

from .config import (
    LogLevel,
    LogFormat,
    LogConfig,
    LoggerConfigManager,
    get_config_manager,
    configure_logger,
)

from .formatters import (
    BaseFormatter,
    SimpleFormatter,
    DetailedFormatter,
    JSONFormatter,
    StructuredFormatter,
    ExecutionLogFormatter,
    FormatterFactory,
    get_formatter,
)

from .handlers import (
    BaseHandler,
    ConsoleHandler,
    FileHandler,
    RotatingFileHandler,
    MemoryHandler,
    WebSocketHandler,
    ExecutionLoggerHandler,
    HandlerFactory,
    create_handler,
)

from .execution import (
    ExecutionLogEntry,
    ExecutionLogger,
    ExecutionLogManager,
    get_execution_logger,
    log_execution,
)

__all__ = [
    # Config
    "LogLevel",
    "LogFormat",
    "LogConfig",
    "LoggerConfigManager",
    "get_config_manager",
    "configure_logger",
    # Formatters
    "BaseFormatter",
    "SimpleFormatter",
    "DetailedFormatter",
    "JSONFormatter",
    "StructuredFormatter",
    "ExecutionLogFormatter",
    "FormatterFactory",
    "get_formatter",
    # Handlers
    "BaseHandler",
    "ConsoleHandler",
    "FileHandler",
    "RotatingFileHandler",
    "MemoryHandler",
    "WebSocketHandler",
    "ExecutionLoggerHandler",
    "HandlerFactory",
    "create_handler",
    # Execution Logger
    "ExecutionLogEntry",
    "ExecutionLogger",
    "ExecutionLogManager",
    "get_execution_logger",
    "log_execution",
]
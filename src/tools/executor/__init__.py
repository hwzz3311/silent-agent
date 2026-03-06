"""
执行器模块（已废弃）

ExecutionPipeline 功能已合并到 BusinessTool.execute() 中。
此模块保留用于避免导入错误。
"""

# 保留基本的 ValidationResult 以避免导入错误
from src.tools.base import ValidationResult

__all__ = [
    "ValidationResult",
]

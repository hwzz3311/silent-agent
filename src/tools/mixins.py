"""
工具模块混入类

提供可复用的混入类以简化工具代码。
"""

from typing import Any


class ToDictMixin:
    """
    混入类: 为 Pydantic BaseModel 自动添加 to_dict 方法

    使用方式:
        class MyResult(BaseModel, ToDictMixin):
            success: bool
            message: str = ""

    然后可以直接调用:
        result = MyResult(success=True, message="done")
        result.to_dict()  # {'success': True, 'message': 'done'}
    """

    def to_dict(self) -> dict:
        """
        转换为字典格式

        自动兼容 Pydantic v1 和 v2:
        - Pydantic v2: 使用 model_dump(exclude_none=True)
        - Pydantic v1: 使用 dict(exclude_none=True)
        """
        if hasattr(self, 'model_dump'):
            return self.model_dump(exclude_none=True)
        return self.dict(exclude_none=True)

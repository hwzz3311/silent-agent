"""
业务级 RPA 工具抽象基类

提供业务工具的统一模板，包含：
- 泛型支持：支持不同的网站适配器
- 统一执行流程：前置检查 → 执行操作 → 后置处理（通过 ExecutionPipeline）
- 日志增强：自动记录操作步骤
- 选择器管理：使用网站选择器集合
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from src.tools.base import Tool, ToolParameters
from src.core.result import Result, ResultMeta
from src.tools.executor import get_default_pipeline

if TYPE_CHECKING:
    from src.tools.base import ExecutionContext


class BusinessToolMeta(type):
    """
    业务工具元类

    用于自动收集工具元信息和验证子类实现。
    """

    def __new__(mcs, name: str, bases: tuple, attrs: dict):
        cls = super().__new__(mcs, name, bases, attrs)

        # 自动收集工具类别
        if not hasattr(cls, 'operation_category'):
            cls.operation_category = "general"

        return cls


class BusinessTool(Tool, ABC):
    """
    业务级 RPA 工具的抽象基类

    特点:
    1. 装饰器驱动：通过 @business_tool 装饰器传入 site_type 和 param_type
    2. 统一错误处理：继承统一错误处理机制
    3. 日志增强：自动记录操作步骤和耗时
    4. 选择器管理：使用网站选择器集合
    5. 执行管道：使用 ExecutionPipeline 进行参数验证、前置检查、重试和后置处理

    Subclass must set (via @business_tool decorator):
        name: str              # 工具名称
        site_type: type       # 对应的 Site 类型

    Subclass can set:
        operation_category: str = "general"  # 操作分类
        version: str = "1.0.0"                # 版本号
        required_login: bool = True           # 是否需要登录

    Usage:
        @business_tool(
            name="xhs_check_login_status",
            site_type=XiaohongshuSite,
            param_type=CheckLoginStatusParams,  # 装饰器传入参数类型
            operation_category="login"
        )
        class CheckLoginStatusTool(BusinessTool):
            async def execute(self, params, context) -> Result:
                # 实现业务逻辑
                pass
    """

    # ========== 类属性（子类必须覆盖） ==========

    #: 工具名称，如 "xhs_check_login_status"
    name: str = "business_tool"

    #: 工具描述
    description: str = "业务操作工具"

    #: 版本号
    version: str = "1.0.0"

    #: 工具分类：login/publish/browse/interact/general
    operation_category: str = "general"

    #: 对应的网站适配器类型（通过装饰器传入）
    site_type: Optional[type] = None

    #: 是否需要登录才能执行
    required_login: bool = True

    # ========== 业务抽象方法（子类必须覆盖） ==========

    @abstractmethod
    async def _execute_core(
        self,
        params: Any,
        context: 'ExecutionContext',
        site: Optional[Any] = None,
    ) -> Result[Any]:
        """
        核心执行逻辑

        子类必须覆盖此方法实现具体的业务逻辑。

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[Any]: 执行结果
        """
        raise NotImplementedError("子类必须实现 _execute_core 方法")

    # ========== 工具方法（领域接口） ==========

    def get_site(self, context: 'ExecutionContext' = None) -> Optional[Any]:
        """
        获取网站适配器实例（每次创建新实例）

        Args:
            context: 执行上下文（可选）

        Returns:
            Optional[Any]: 网站适配器实例，如果 site_type 为 None 返回 None
        """
        if self.site_type is None:
            return None

        # 每次创建新实例，避免状态共享和多线程竞争
        site = self.site_type()

        # 更新超时和重试配置
        if context:
            if hasattr(site.config, 'timeout'):
                site.config.timeout = context.timeout
            if hasattr(site.config, 'retry_count'):
                site.config.retry_count = context.retry_count

        return site

    def get_selector(self, key: str) -> Optional[str]:
        """
        获取选择器

        优先使用工具自己的选择器，如果没有则从网站适配器获取。

        Args:
            key: 选择器名称

        Returns:
            Optional[str]: 选择器值
        """
        # 首先检查工具自己的选择器
        if hasattr(self, 'selectors'):
            selector = getattr(self.selectors, key, None)
            if selector:
                return selector

        # 如果没有，从网站适配器获取
        site = self.get_site()
        return getattr(site.selectors, key, None)

    def get_params_type(self) -> Any:
        """
        获取参数类型（用于动态创建参数）

        Returns:
            Any: 参数类型
        """
        # 通过装饰器或属性获取参数类型
        if hasattr(self, 'param_type') and self.param_type is not None:
            return self.param_type
        return ToolParameters

    def get_result_type(self) -> type:
        """
        获取结果类型

        Returns:
            type: 结果类型
        """
        return type

    # ========== 执行方法（委托给 ExecutionPipeline） ==========

    async def execute(
        self,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result:
        """
        执行工具（实现抽象方法）

        委托给 ExecutionPipeline 执行完整的流程：参数验证 → 前置检查 → 核心执行 → 后置处理。
        ExecutionPipeline 会自动处理重试逻辑。

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[Any]: 执行结果
        """
        # 使用默认执行管道（包含验证、前置检查、重试、后置处理）
        pipeline = get_default_pipeline()
        return await pipeline.execute(self, params, context)

    async def execute_with_validation(
        self,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result:
        """
        带验证的执行（保持兼容）

        委托给 ExecutionPipeline 执行完整流程（包含参数验证）。

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result: 执行结果
        """
        # 使用默认执行管道
        pipeline = get_default_pipeline()
        return await pipeline.execute(self, params, context)

    async def execute_with_retry(
        self,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result:
        """
        带重试的执行（保持兼容）

        委托给 ExecutionPipeline 执行完整流程（包含重试逻辑）。

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result: 执行结果
        """
        # 使用默认执行管道（已包含重试逻辑）
        pipeline = get_default_pipeline()
        return await pipeline.execute(self, params, context)

    # ========== 类方法 ==========

    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """
        获取工具元信息

        Returns:
            Dict[str, Any]: 工具信息字典
        """
        return {
            "name": cls.name,
            "description": cls.description,
            "version": cls.version,
            "category": cls.operation_category,
            "site_type": cls.site_type.__name__ if cls.site_type else None,
            "required_login": cls.required_login,
        }

    @classmethod
    def list_operation_categories(cls) -> List[str]:
        """
        获取所有支持的操作类别

        Returns:
            List[str]: 操作类别列表
        """
        return [
            "login",       # 登录相关
            "publish",     # 发布相关
            "browse",      # 浏览相关
            "interact",    # 互动相关
            "general",     # 通用操作
        ]

    # ========== 字符串表示 ==========

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"name={self.name}, "
            f"category={self.operation_category}, "
            f"site={self.site_type.__name__ if self.site_type else 'unknown'}"
            f")>"
        )

    def __str__(self) -> str:
        return (
            f"{self.name} "
            f"({self.operation_category}) "
            f"- {self.description}"
        )


# 便捷类型别名
# BusinessToolType = TypeVar('BusinessToolType', bound=BusinessTool)


def create_business_tool(
    name: str,
    description: str,
    site_type: Optional[type] = None,
    operation_category: str = "general",
    version: str = "1.0.0"
):
    """
    动态创建业务工具类的装饰器函数

    Args:
        name: 工具名称
        description: 工具描述
        site_type: 网站适配器类型
        operation_category: 操作类别
        version: 版本号

    Returns:
        装饰器函数

    Usage:
        CheckLoginStatusTool = create_business_tool(
            name="xhs_check_login_status",
            description="检查小红书登录状态",
            site_type=XiaohongshuSite,
            operation_category="login"
        )
    """
    def decorator(cls: type):
        cls.name = name
        cls.description = description
        cls.site_type = site_type
        cls.operation_category = operation_category
        cls.version = version
        return cls

    return decorator


__all__ = [
    "BusinessTool",
    "BusinessToolMeta",
    "create_business_tool",
]

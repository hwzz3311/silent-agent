"""
业务级 RPA 工具抽象基类

提供业务工具的统一模板，包含：
- 泛型支持：支持不同的网站适配器
- 统一执行流程：前置检查 → 执行操作 → 后置处理
- 日志增强：自动记录操作步骤
- 选择器管理：使用网站选择器集合
"""

from abc import ABC
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from src.tools.base import Tool, ToolParameters
from src.core.result import Result, ResultMeta, Error

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

    # ========== 工具实现 ==========

    async def execute_with_validation(
        self,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result:
        """
        带验证的执行（覆盖父类方法添加业务逻辑）

        统一执行流程:
        1. 前置检查（登录状态、页面状态等）
        2. 获取网站适配器实例
        3. 执行操作
        4. 后置处理
        5. 返回结果
        """
        # 验证参数
        validation = await self.validate_params(params)
        if not validation.valid:
            return Result.fail(
                error=Error.validation(
                    message="参数验证失败",
                    details={"errors": validation.errors}
                ),
                meta=ResultMeta(
                    tool_name=self.name,
                    duration_ms=0,
                    attempt=1
                )
            )

        try:
            # 1. 前置检查
            pre_check = await self._pre_execute(params, context)
            if not pre_check.success:
                return pre_check

            # 2. 获取网站适配器
            site = self.get_site(context)

            # 3. 执行核心操作
            result = await self._execute_core(params, context)

            # 4. 后置处理
            final_result = await self._post_execute(result, params, context)

            return final_result

        except Exception as e:
            return self.error_from_exception(e)

    async def execute_with_retry(
        self,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result:
        """
        带重试的执行（覆盖父类方法）

        在父类重试逻辑基础上增加业务特定的重试策略。
        """
        last_error = None
        site = None

        for attempt in range(1, context.retry_count + 1):
            try:
                # 重试时重新获取网站适配器
                site = self.get_site(context)

                result = await self.execute_with_validation(params, context)

                if result.success:
                    if result.meta:
                        result.meta.attempt = attempt
                    return result

                # 如果是不可恢复错误，直接返回
                if result.error and result.error.recoverable is False:
                    return result

                last_error = result.error

            except Exception as e:
                from .errors import BusinessException
                if isinstance(e, BusinessException):
                    # 业务异常通常不可恢复
                    return Result.fail(
                        error=e,
                        meta=ResultMeta(
                            tool_name=self.name,
                            attempt=attempt,
                            duration_ms=attempt * context.retry_delay
                        )
                    )
                last_error = e

            # 等待后重试
            if attempt < context.retry_count:
                await self._sleep(context.retry_delay)

        # 所有尝试都失败
        return Result.fail(
            error=Error.from_exception(last_error) if last_error else Error.unknown("执行失败"),
            meta=ResultMeta(
                tool_name=self.name,
                attempt=context.retry_count,
                duration_ms=context.retry_count * context.retry_delay
            )
        )

    # ========== 子类可覆盖的方法 ==========

    async def _pre_execute(
        self,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result[bool]:
        """
        前置检查

        默认实现:
        - 检查登录状态（如果 required_login=True）
        - 检查页面状态

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[bool]: 检查是否通过
        """
        from .errors import BusinessErrorCode

        # 检查是否需要登录
        if self.required_login:
            site = self.get_site(context)
            if site is None:
                return Result.fail(
                    error=Error(
                        code="SITE_NOT_FOUND",
                        message=f"工具 {self.name} 未配置 site_type，无法执行需要登录的检查",
                        recoverable=False,
                    ),
                    meta=ResultMeta(
                        tool_name=self.name,
                        duration_ms=0
                    )
                )
            login_result = await site.check_login_status(context, silent=True)

            if login_result.success:
                if not login_result.data.get("is_logged_in", False):
                    return Result.fail(
                        error=Error(
                            code=BusinessErrorCode.LOGIN_REQUIRED.value,
                            message=f"需要登录后才能执行操作 {self.name}",
                            recoverable=True,
                            details={
                                "site_name": site.site_name,
                                "operation": self.name,
                                "suggestion": "请先调用登录工具或等待用户登录"
                            }
                        ),
                        meta=ResultMeta(
                            tool_name=self.name,
                            duration_ms=0
                        )
                    )
            else:
                return Result.fail(
                    error=Error.unknown(
                        message="无法检查登录状态",
                        details={"error": str(login_result.error)}
                    )
                )

        return Result.ok(True)

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

    async def _post_execute(
        self,
        result: Result,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result:
        """
        后置处理

        默认实现直接返回结果。子类可以覆盖此方法添加:
        - 结果验证
        - 清理操作
        - 日志记录

        Args:
            result: 执行结果
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[Any]: 处理后的结果
        """
        # 如果结果不是 Result 类型，包装为 Result
        from src.core.result import Result as CoreResult
        if not isinstance(result, CoreResult):
            # 将 BaseModel 结果包装为 Result
            if hasattr(result, 'success'):
                return CoreResult.ok(
                    data=result,
                    meta=ResultMeta(
                        tool_name=self.name,
                        duration_ms=0
                    )
                )
            else:
                return CoreResult.fail(
                    error=Error.unknown(
                        message="执行返回了非 Result 类型的结果",
                        details={"result_type": type(result).__name__}
                    ),
                    meta=ResultMeta(
                        tool_name=self.name,
                        duration_ms=0
                    )
                )
        return result

    # ========== 工具方法 ==========

    def get_site(self, context: 'ExecutionContext' = None) -> Optional[Any]:
        """
        获取网站适配器实例

        Args:
            context: 执行上下文（可选）

        Returns:
            Optional[Any]: 网站适配器实例，如果 site_type 为 None 返回 None
        """
        if self.site_type is None:
            return None

        # 使用单例模式缓存站点实例
        if not hasattr(self, '_site_instance') or self._site_instance is None:
            self._site_instance = self.site_type()

        # 更新超时和重试配置
        if context:
            if hasattr(self._site_instance.config, 'timeout'):
                self._site_instance.config.timeout = context.timeout
            if hasattr(self._site_instance.config, 'retry_count'):
                self._site_instance.config.retry_count = context.retry_count

        return self._site_instance

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
            site = self.get_site()
            selector = getattr(site.selectors, key, None)
            if selector:
                return selector

        return None

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

    async def execute(
        self,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result:
        """
        执行工具（实现抽象方法）

        直接调用 execute_with_retry，使用统一的业务执行流程。

        Args:
            params: 工具参数
            context: 执行上下文

        Returns:
            Result[Any]: 执行结果
        """
        return await self.execute_with_retry(params, context)

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
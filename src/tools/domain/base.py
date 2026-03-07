"""
业务级 RPA 工具抽象基类

提供业务工具的统一模板，包含：
- 泛型支持：支持不同的网站适配器
- 统一执行流程：参数验证 → 核心执行（含重试）
- 日志增强：自动记录操作步骤
- 选择器管理：使用网站选择器集合
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from src.tools.base import Tool, ToolParameters
from src.core.result import Result, ResultMeta

if TYPE_CHECKING:
    from src.tools.base import ExecutionContext


class BusinessTool(Tool, ABC):
    """
    业务级 RPA 工具的抽象基类

    特点:
    1. 装饰器驱动：通过 @business_tool 装饰器传入 site_type 和 param_type
    2. 统一错误处理：继承统一错误处理机制
    3. 日志增强：自动记录操作步骤和耗时
    4. 选择器管理：使用网站选择器集合
    5. 执行管道：直接执行核心逻辑（含参数验证、重试）

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
        # 首先检查工具自己的选择器（支持字典格式）
        if hasattr(self, 'selectors'):
            if isinstance(self.selectors, dict):
                selector = self.selectors.get(key)
            else:
                selector = getattr(self.selectors, key, None)
            if selector:
                return selector

        # 如果没有，从网站适配器获取
        site = self.get_site()
        # 将 BaseModel 转为字典后获取
        selectors_dict = site.selectors.model_dump() if hasattr(site.selectors, 'model_dump') else {}
        return selectors_dict.get(key) or getattr(site.selectors, key, None)

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

    # ========== 执行方法（统一由父类处理验证+重试） ==========

    async def execute(
        self,
        params: ToolParameters,
        context: 'ExecutionContext'
    ) -> Result:
        """
        执行工具（实现抽象方法）

        直接执行核心逻辑，子类自己处理重试。

        Args:
            param: 工具参数
            context: 执行上下文

        Returns:
            Result[Any]: 执行结果
        """
        # 1. 获取站点实例
        site = self.get_site(context)

        # 2. 执行核心逻辑
        start_time = time.time()
        result = await self._execute_core(params, context, site)

        # 3. 记录执行时间
        if result.meta:
            result.meta.duration_ms = int((time.time() - start_time) * 1000)

        return result

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


import logging
import re
from typing import Optional, Type, Callable

from .registry import BusinessToolRegistry, get_registry

logger = logging.getLogger(__name__)


def business_tool(
    name: str = None,
    site_type: Type = None,
    param_type: Type = None,
    operation_category: str = "general",
    version: str = "1.0.0",
    required_login: bool = True,
    enabled: bool = True,
) -> Callable[[Type], Type]:
    """
    业务工具装饰器

    自动注册工具类到 BusinessToolRegistry。

    Args:
        name: 工具名称，如 "xhs_check_login_status"
        site_type: 站点适配器类型，如 XiaohongshuSite
        param_type: 参数类型（如 CheckLoginStatusParams），通过装饰器传入
        operation_category: 操作分类，如 "login", "browse", "publish", "interact"
        version: 版本号，默认 "1.0.0"
        required_login: 是否需要登录，默认 True
        enabled: 是否启用注册，默认 True

    Returns:
        装饰器函数

    Usage:
        @business_tool(
            name="xhs_check_login_status",
            site_type=XiaohongshuSite,
            param_type=CheckLoginStatusParams,
            operation_category="login"
        )
        class CheckLoginStatusTool(BusinessTool):
            description = "检查小红书登录状态"
            ...
    """
    def decorator(cls: Type) -> Type:
        # 验证类是 BusinessTool 的子类
        if not (isinstance(cls, type) and issubclass(cls, BusinessTool) and cls is not BusinessTool):
            raise TypeError(f"@business_tool 只能用于 BusinessTool 的子类，收到: {cls}")

        # 设置类属性
        if name:
            cls.name = name
        elif not hasattr(cls, 'name') or not cls.name:
            # 从类名自动生成名称
            cls.name = _auto_generate_name(cls)

        cls.operation_category = operation_category
        cls.version = version
        cls.required_login = required_login

        if site_type:
            cls.site_type = site_type

        # 设置参数类型（通过装饰器传入）
        if param_type:
            cls.__parameter_type__ = param_type

        # 自动注册到注册表
        if enabled:
            get_registry().register_by_class(cls, enabled=True)
            logger.info(f"Registered tool '{cls.name}' via @business_tool decorator")

        return cls

    return decorator


def _auto_generate_name(cls: Type) -> str:
    """
    从类名自动生成工具名称

    例如:
        CheckLoginStatusTool -> xhs_check_login_status
        ListFeedsTool -> xhs_list_feeds
    """
    class_name = cls.__name__

    # 移除 Tool 后缀
    if class_name.endswith('Tool'):
        class_name = class_name[:-4]

    # 转换为蛇形命名
    name = re.sub(r'(?<!^)([A-Z])', r'_\1', class_name).lower().strip('_')

    return f"{name}_tool"


__all__ = [
    "BusinessTool",
    "business_tool",
]

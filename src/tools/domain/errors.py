"""
业务错误处理

提供统一的错误类型定义和异常处理。
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional, Any, Dict
from pydantic import BaseModel

if TYPE_CHECKING:
    pass


class BusinessErrorCode(str, Enum):
    """
    业务错误代码

    错误代码分类:
    - LOGIN_*: 登录相关错误
    - PAGE_*: 页面相关错误
    - ELEMENT_*: 元素相关错误
    - TIMEOUT_*: 超时相关错误
    - EXTRACTION_*: 数据提取相关错误
    - VALIDATION_*: 验证相关错误
    - SITE_*: 网站相关错误
    - RATE_*: 频率限制相关错误
    - INTERNAL_*: 内部错误
    """

    # 通用
    UNKNOWN = "UNKNOWN"

    # 登录相关
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGIN_EXPIRED = "LOGIN_EXPIRED"
    LOGIN_INVALID = "LOGIN_INVALID"

    # 页面相关
    PAGE_NOT_FOUND = "PAGE_NOT_FOUND"
    PAGE_LOAD_FAILED = "PAGE_LOAD_FAILED"
    PAGE_STRUCTURE_CHANGED = "PAGE_STRUCTURE_CHANGED"

    # 元素相关
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_NOT_VISIBLE = "ELEMENT_NOT_VISIBLE"
    ELEMENT_NOT_INTERACTABLE = "ELEMENT_NOT_INTERACTABLE"
    ELEMENT_STALE = "ELEMENT_STALE"

    # 超时相关
    TIMEOUT = "TIMEOUT"
    TIMEOUT_WAITING = "TIMEOUT_WAITING"
    TIMEOUT_DOWNLOAD = "TIMEOUT_DOWNLOAD"
    TIMEOUT_UPLOAD = "TIMEOUT_UPLOAD"

    # 数据提取相关
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EXTRACTION_INVALID_FORMAT = "EXTRACTION_INVALID_FORMAT"

    # 验证相关
    VALIDATION_FAILED = "VALIDATION_FAILED"
    VALIDATION_MISSING_FIELD = "VALIDATION_MISSING_FIELD"
    VALIDATION_INVALID_VALUE = "VALIDATION_INVALID_VALUE"

    # 网站相关
    SITE_NOT_SUPPORTED = "SITE_NOT_SUPPORTED"
    SITE_STRUCTURE_CHANGED = "SITE_STRUCTURE_CHANGED"
    SITE_RESPONSE_ERROR = "SITE_RESPONSE_ERROR"

    # 频率限制
    RATE_LIMITED = "RATE_LIMITED"
    RATE_LIMITED_API = "RATE_LIMITED_API"

    # 内部错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INTERNAL_ASSERTION = "INTERNAL_ASSERTION"

    # 文件操作
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_READ_FAILED = "FILE_READ_FAILED"
    FILE_WRITE_FAILED = "FILE_WRITE_FAILED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"

    # 网络相关
    NETWORK_ERROR = "NETWORK_ERROR"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    NETWORK_OFFLINE = "NETWORK_OFFLINE"

    @property
    def category(self) -> str:
        """获取错误类别"""
        return self.name.split('_')[0].lower()

    @property
    def is_recoverable(self) -> bool:
        """
        判断错误是否可恢复

        Returns:
            bool: 是否可恢复
        """
        unrecoverable = [
            BusinessErrorCode.SITE_STRUCTURE_CHANGED,
            BusinessErrorCode.PAGE_NOT_FOUND,
            BusinessErrorCode.VALIDATION_FAILED,
            BusinessErrorCode.INTERNAL_ERROR,
        ]
        return self not in unrecoverable


class BusinessError(BaseModel):
    """
    业务错误信息

    用于结构化描述业务操作中发生的错误。

    Attributes:
        code: 错误代码
        message: 错误消息
        details: 额外详情信息
        site_name: 网站名称
        operation: 发生错误的操作名称
        selector: 相关的 CSS 选择器
        suggestion: 修复建议
        caused_by: 原始异常信息
    """
    code: BusinessErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    site_name: Optional[str] = None
    operation: Optional[str] = None
    selector: Optional[str] = None
    suggestion: Optional[str] = None
    caused_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code.value if isinstance(self.code, BusinessErrorCode) else self.code,
            "message": self.message,
            "details": self.details,
            "site_name": self.site_name,
            "operation": self.operation,
            "selector": self.selector,
            "suggestion": self.suggestion,
            "caused_by": self.caused_by,
        }

    @property
    def is_recoverable(self) -> bool:
        """判断错误是否可恢复"""
        if isinstance(self.code, BusinessErrorCode):
            return self.code.is_recoverable
        return True

    def to_exception_message(self) -> str:
        """生成异常消息字符串"""
        parts = [self.message]

        if self.suggestion:
            parts.append(f"建议: {self.suggestion}")

        if self.operation:
            parts.append(f"操作: {self.operation}")

        if self.selector:
            parts.append(f"选择器: {self.selector}")

        return " | ".join(parts)


class BusinessException(Exception):
    """
    业务异常

    在业务操作中抛出此异常来表示业务逻辑错误。

    Usage:
        raise BusinessException.login_required("xiaohongshu")

        # 或使用详细错误
        raise BusinessException(
            code=BusinessErrorCode.ELEMENT_NOT_FOUND,
            message="找不到点赞按钮",
            selector=".like-button",
            operation="xhs_like_feed",
            suggestion="请检查选择器是否正确，小红书可能已更新页面结构"
        )
    """

    def __init__(
        self,
        code: BusinessErrorCode,
        message: str,
        site_name: str = None,
        operation: str = None,
        selector: str = None,
        suggestion: str = None,
        details: Dict[str, Any] = None,
        caused_by: Exception = None
    ):
        self.code = code
        self.message = message
        self.site_name = site_name
        self.operation = operation
        self.selector = selector
        self.suggestion = suggestion
        self.details = details or {}
        self.caused_by = str(caused_by) if caused_by else None

        # 构建完整消息
        full_message = self._build_message()

        super().__init__(full_message)

    def _build_message(self) -> str:
        """构建异常消息"""
        parts = [self.message]

        if self.suggestion:
            parts.append(f"建议: {self.suggestion}")

        if self.operation:
            parts.append(f"操作: {self.operation}")

        if self.selector:
            parts.append(f"选择器: {self.selector}")

        return " | ".join(parts)

    def to_error(self) -> BusinessError:
        """
        转换为 BusinessError 对象

        Returns:
            BusinessError: 错误信息对象
        """
        return BusinessError(
            code=self.code,
            message=self.message,
            details=self.details,
            site_name=self.site_name,
            operation=self.operation,
            selector=self.selector,
            suggestion=self.suggestion,
            caused_by=self.caused_by,
        )

    # ========== 工厂方法 ==========

    @classmethod
    def login_required(
        cls,
        site_name: str = None,
        suggestion: str = "请先调用登录工具或等待用户登录"
    ) -> 'BusinessException':
        """
        创建需要登录异常

        Args:
            site_name: 网站名称
            suggestion: 修复建议

        Returns:
            BusinessException: 异常实例
        """
        return cls(
            code=BusinessErrorCode.LOGIN_REQUIRED,
            message="需要登录后才能执行此操作",
            site_name=site_name,
            suggestion=suggestion
        )

    @classmethod
    def element_not_found(
        cls,
        selector: str,
        operation: str = None,
        site_name: str = None,
        suggestion: str = None
    ) -> 'BusinessException':
        """
        创建元素未找到异常

        Args:
            selector: CSS 选择器
            operation: 操作名称
            site_name: 网站名称
            suggestion: 修复建议

        Returns:
            BusinessException: 异常实例
        """
        return cls(
            code=BusinessErrorCode.ELEMENT_NOT_FOUND,
            message=f"找不到元素: {selector}",
            operation=operation,
            site_name=site_name,
            selector=selector,
            suggestion=suggestion or f"请检查选择器 '{selector}' 是否正确"
        )

    @classmethod
    def page_not_found(
        cls,
        url: str,
        operation: str = None,
        site_name: str = None,
        suggestion: str = None
    ) -> 'BusinessException':
        """
        创建页面未找到异常

        Args:
            url: 页面 URL
            operation: 操作名称
            site_name: 网站名称
            suggestion: 修复建议

        Returns:
            BusinessException: 异常实例
        """
        return cls(
            code=BusinessErrorCode.PAGE_NOT_FOUND,
            message=f"无法访问页面: {url}",
            operation=operation,
            site_name=site_name,
            suggestion=suggestion or "请检查 URL 是否正确"
        )

    @classmethod
    def timeout(
        cls,
        operation: str,
        timeout: int = None,
        site_name: str = None,
        suggestion: str = None
    ) -> 'BusinessException':
        """
        创建超时异常

        Args:
            operation: 操作名称
            timeout: 超时时间
            site_name: 网站名称
            suggestion: 修复建议

        Returns:
            BusinessException: 异常实例
        """
        return cls(
            code=BusinessErrorCode.TIMEOUT,
            message=f"操作超时: {operation}",
            operation=operation,
            site_name=site_name,
            details={"timeout_ms": timeout},
            suggestion=suggestion or "网络不稳定，请稍后重试"
        )

    @classmethod
    def site_structure_changed(
        cls,
        site_name: str,
        operation: str = None,
        suggestion: str = "网站结构可能已更新，请检查并更新选择器"
    ) -> 'BusinessException':
        """
        创建网站结构变化异常

        Args:
            site_name: 网站名称
            operation: 操作名称
            suggestion: 修复建议

        Returns:
            BusinessException: 异常实例
        """
        return cls(
            code=BusinessErrorCode.SITE_STRUCTURE_CHANGED,
            message=f"{site_name} 网站结构可能已更新",
            operation=operation,
            site_name=site_name,
            suggestion=suggestion
        )

    @classmethod
    def extraction_failed(
        cls,
        data_type: str,
        operation: str = None,
        site_name: str = None,
        suggestion: str = None
    ) -> 'BusinessException':
        """
        创建数据提取失败异常

        Args:
            data_type: 数据类型
            operation: 操作名称
            site_name: 网站名称
            suggestion: 修复建议

        Returns:
            BusinessException: 异常实例
        """
        return cls(
            code=BusinessErrorCode.EXTRACTION_FAILED,
            message=f"提取数据失败: {data_type}",
            operation=operation,
            site_name=site_name,
            suggestion=suggestion or "请检查页面结构是否已更新"
        )

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        operation: str = None,
        site_name: str = None
    ) -> 'BusinessException':
        """
        从通用异常创建业务异常

        Args:
            exception: 原始异常
            operation: 操作名称
            site_name: 网站名称

        Returns:
            BusinessException: 业务异常实例
        """
        # 根据异常类型映射到业务错误代码
        error_mapping = {
            "ElementNotFound": BusinessErrorCode.ELEMENT_NOT_FOUND,
            "TimeoutError": BusinessErrorCode.TIMEOUT,
            "ValueError": BusinessErrorCode.VALIDATION_FAILED,
            "KeyError": BusinessErrorCode.EXTRACTION_FAILED,
            "ConnectionError": BusinessErrorCode.NETWORK_ERROR,
        }

        error_code = BusinessErrorCode.UNKNOWN
        error_message = str(exception)

        for exc_type, code in error_mapping.items():
            if exc_type in type(exception).__name__:
                error_code = code
                break

        return cls(
            code=error_code,
            message=error_message,
            operation=operation,
            site_name=site_name,
            caused_by=exception
        )

    def __reduce__(self):
        """支持 Pickle 序列化"""
        return (
            self.__class__,
            (
                self.code,
                self.message,
                self.site_name,
                self.operation,
                self.selector,
                self.suggestion,
                self.details,
                self.caused_by
            )
        )


class ErrorSuggestion:
    """
    错误建议生成器

    根据错误类型自动生成修复建议。
    """

    @staticmethod
    def for_element_not_found(selector: str) -> str:
        """
        为元素未找到错误生成建议

        Args:
            selector: CSS 选择器

        Returns:
            str: 建议文本
        """
        return (
            f"请检查选择器 '{selector}' 是否正确:\n"
            f"1. 确认小红书页面结构是否已更新\n"
            f"2. 使用浏览器开发者工具检查元素是否存在\n"
            f"3. 尝试使用备用选择器"
        )

    @staticmethod
    def for_site_structure_changed(site_name: str) -> str:
        """
        为网站结构变化错误生成建议

        Args:
            site_name: 网站名称

        Returns:
            str: 建议文本
        """
        return (
            f"{site_name} 的页面结构可能已更新:\n"
            f"1. 使用浏览器开发者工具检查最新页面结构\n"
            f"2. 更新对应的选择器\n"
            f"3. 运行测试用例验证修复效果"
        )

    @staticmethod
    def for_timeout(operation: str) -> str:
        """
        为超时错误生成建议

        Args:
            operation: 操作名称

        Returns:
            str: 建议文本
        """
        return (
            f"操作 '{operation}' 超时:\n"
            f"1. 检查网络连接是否稳定\n"
            f"2. 尝试增加超时时间\n"
            f"3. 稍后重试操作"
        )

    @staticmethod
    def for_login_required(operation: str) -> str:
        """
        为需要登录错误生成建议

        Args:
            operation: 操作名称

        Returns:
            str: 建议文本
        """
        return (
            f"操作 '{operation}' 需要登录:\n"
            f"1. 先调用登录相关工具完成登录\n"
            f"2. 确认登录状态有效\n"
            f"3. 登录成功后再执行此操作"
        )


__all__ = [
    "BusinessErrorCode",
    "BusinessError",
    "BusinessException",
    "ErrorSuggestion",
]
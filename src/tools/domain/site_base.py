"""
网站适配器抽象基类

定义网站 RPA 操作的统一接口，支持跨网站复用。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, Any
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.tools.base import ExecutionContext

from src.core.result import Result, Error, ErrorCode


class SiteConfig(BaseModel):
    """
    网站配置

    Attributes:
        site_name: 网站唯一标识符
        base_url: 网站基础 URL
        timeout: 默认超时时间（毫秒）
        retry_count: 默认重试次数
        need_login: 是否需要登录才能执行操作
    """
    site_name: str = Field(..., description="网站唯一标识符")
    base_url: str = Field(..., description="网站基础 URL")
    timeout: int = Field(default=30000, ge=1000, le=300000, description="默认超时时间（毫秒）")
    retry_count: int = Field(default=3, ge=1, le=10, description="默认重试次数")
    need_login: bool = Field(default=True, description="是否需要登录")


class SiteSelectorSet(BaseModel):
    """
    网站通用选择器集合

    定义所有网站都应该具备的通用选择器。

    Attributes:
        login_button: 登录按钮选择器
        logout_button: 登出按钮选择器
        user_avatar: 用户头像选择器
        username_display: 用户名显示选择器
        modal_overlay: 弹窗遮罩层选择器
        confirm_button: 确认按钮选择器
        cancel_button: 取消按钮选择器
        cookie_accept_button: 接受 Cookie 按钮选择器
    """
    # 登录相关
    login_button: Optional[str] = Field(default=None, description="登录按钮选择器")
    logout_button: Optional[str] = Field(default=None, description="登出按钮选择器")
    user_avatar: Optional[str] = Field(default=None, description="用户头像选择器")
    username_display: Optional[str] = Field(default=None, description="用户名显示选择器")

    # 弹窗/对话框
    modal_overlay: Optional[str] = Field(default=None, description="弹窗遮罩层选择器")
    confirm_button: Optional[str] = Field(default=None, description="确认按钮选择器")
    cancel_button: Optional[str] = Field(default=None, description="取消按钮选择器")

    # Cookie 弹窗
    cookie_accept_button: Optional[str] = Field(default=None, description="接受 Cookie 按钮选择器")


class PageInfo(BaseModel):
    """
    页面信息

    用于描述当前页面状态的信息。

    Attributes:
        url: 当前页面 URL
        title: 页面标题
        is_login_page: 是否为登录页面
        is_logged_in: 是否已登录
    """
    url: Optional[str] = None
    title: Optional[str] = None
    is_login_page: bool = False
    is_logged_in: bool = False


class Site(ABC):
    """
    网站 RPA 操作的抽象基类

    所有网站适配器都应该继承此类并实现以下方法：
    - navigate(): 导航到指定页面
    - check_login_status(): 检查登录状态
    - extract_data(): 提取页面数据
    - wait_for_element(): 等待元素出现

    Usage:
        class MySite(Site):
            config = MySiteConfig(...)
            selectors = MySiteSelectors(...)

            async def navigate(self, page: str, context) -> bool:
                # 实现导航逻辑
                pass

            async def check_login_status(self, context) -> Dict[str, Any]:
                # 实现登录检查逻辑
                pass
    """

    # 子类必须设置
    config: SiteConfig
    selectors: SiteSelectorSet

    @property
    def site_name(self) -> str:
        """获取网站名称"""
        return self.config.site_name

    @property
    def base_url(self) -> str:
        """获取基础 URL"""
        return self.config.base_url

    # ========== 抽象方法 ==========

    @abstractmethod
    async def navigate(
        self,
        page: str,
        page_id: Optional[str] = None,
        context: 'ExecutionContext' = None
    ) -> Result[bool]:
        """
        导航到指定页面

        Args:
            page: 页面类型标识（如 'home', 'profile', 'feed' 等）
            page_id: 页面 ID（如用户 ID、笔记 ID 等）
            context: 执行上下文

        Returns:
            Result[bool]: 导航是否成功
        """
        ...

    @abstractmethod
    async def check_login_status(
        self,
        context: 'ExecutionContext' = None,
        silent: bool = False
    ) -> Result[Dict[str, Any]]:
        """
        检查当前页面的登录状态

        Returns:
            Result[Dict]: 包含以下字段的字典
                - is_logged_in: bool, 是否已登录
                - username: Optional[str], 用户名
                - user_id: Optional[str], 用户 ID
                - avatar: Optional[str], 头像 URL
        """
        ...

    @abstractmethod
    async def extract_data(
        self,
        data_type: str,
        context: 'ExecutionContext' = None,
        max_items: int = 20
    ) -> Result[Any]:
        """
        提取页面数据

        Args:
            data_type: 数据类型标识
            context: 执行上下文
            max_items: 最大提取数量

        Returns:
            Result[Any]: 提取的数据
        """
        ...

    @abstractmethod
    async def wait_for_element(
        self,
        selector: str,
        timeout: int = 10000,
        context: 'ExecutionContext' = None
    ) -> Result[bool]:
        """
        等待元素出现在页面中

        Args:
            selector: CSS 选择器
            timeout: 超时时间（毫秒）
            context: 执行上下文

        Returns:
            Result[bool]: 元素是否出现
        """
        ...

    # ========== 工具方法 ==========

    def get_selector(self, key: str) -> Optional[str]:
        """
        获取选择器

        Args:
            key: 选择器名称

        Returns:
            Optional[str]: 选择器值，不存在返回 None
        """
        # 直接使用字典访问
        selectors_dict = self.selectors.model_dump() if hasattr(self.selectors, 'model_dump') else {}
        return selector_dict.get(key) or getattr(self.selectors, key, None)

    def _create_default_context(self) -> 'ExecutionContext':
        """创建默认执行上下文"""
        from src.tools.base import ExecutionContext
        return ExecutionContext(
            timeout=self.config.timeout,
            retry_count=self.config.retry_count
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(site={self.site_name})>"

    def __str__(self) -> str:
        return f"{self.site_name} (base_url={self.base_url})"


__all__ = [
    "Site",
    "SiteConfig",
    "SiteSelectorSet",
    "PageInfo",
]
"""
浏览器管理 API 路由

提供浏览器实例的注册、查询、注销功能。
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from src.api.schemas.browser import (
    RegisterBrowserRequest,
    RegisterBrowserResponse,
    BrowserInstanceInfo,
    BrowserListResponse,
    BrowserHealthResponse,
)
from src.api.schemas import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 浏览器实例管理 ====================

@router.post(
    "/register",
    response_model=RegisterBrowserResponse,
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
    },
    summary="注册浏览器实例",
    description="注册新的浏览器实例",
)
async def register_browser(request: RegisterBrowserRequest):
    """
    注册新的浏览器实例

    请求体:
    - **mode**: 浏览器模式（extension/puppeteer/hybrid）
    - **secret_key**: 扩展密钥（Extension/Hybrid 模式用）
    - **ws_endpoint**: WebSocket 端点（Puppeteer/Hybrid 模式用）
    - **relay_host**: Relay 服务器主机
    - **relay_port**: Relay 服务器端口
    """
    from src.adapters.browser import get_browser_manager, BrowserInstance, BrowserMode

    # 获取管理器
    manager = get_browser_manager()

    # 创建浏览器实例
    instance = BrowserInstance(
        mode=BrowserMode(request.mode),
        secret_key=request.secret_key,
        ws_endpoint=request.ws_endpoint,
        relay_host=request.relay_host,
        relay_port=request.relay_port,
    )

    # 检查是否已有默认实例
    existing_default = manager.get_instance()
    is_default = existing_default is None

    # 注册实例
    instance_id = manager.register_instance(instance)

    logger.info(f"[Browser API] 注册浏览器实例: {instance_id}, 模式: {request.mode}")

    return RegisterBrowserResponse(
        instance_id=instance_id,
        mode=request.mode,
        is_default=is_default,
    )


@router.get(
    "/list",
    response_model=BrowserListResponse,
    summary="列出浏览器实例",
    description="列出所有注册的浏览器实例",
)
async def list_browsers():
    """
    列出所有浏览器实例

    返回所有注册的浏览器实例列表。
    """
    from src.adapters.browser import get_browser_manager

    manager = get_browser_manager()
    instances = manager.list_instances()

    # 转换为 Pydantic 模型
    instance_infos = [
        BrowserInstanceInfo(
            instance_id=inst["instance_id"],
            mode=inst["mode"],
            secret_key=inst.get("secret_key"),
            ws_endpoint=inst.get("ws_endpoint"),
            relay_host=inst.get("relay_host", "127.0.0.1"),
            relay_port=inst.get("relay_port", 18792),
            is_connected=inst.get("is_connected", False),
            created_at=inst.get("created_at"),
        )
        for inst in instances
    ]

    return BrowserListResponse(
        instances=instance_infos,
        total=len(instance_infos),
    )


@router.delete(
    "/{instance_id}",
    summary="注销浏览器实例",
    description="注销指定的浏览器实例",
)
async def unregister_browser(instance_id: str):
    """
    注销浏览器实例

    - **instance_id**: 浏览器实例 ID
    """
    from src.adapters.browser import get_browser_manager

    manager = get_browser_manager()
    success = manager.unregister_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"浏览器实例不存在: {instance_id}",
        )

    return {"message": "实例已注销", "instance_id": instance_id}


@router.get(
    "/{instance_id}/health",
    response_model=BrowserHealthResponse,
    summary="实例健康检查",
    description="检查浏览器实例的连接状态",
)
async def browser_health(instance_id: str):
    """
    检查实例连接状态

    - **instance_id**: 浏览器实例 ID
    """
    from src.adapters.browser import get_browser_manager

    manager = get_browser_manager()
    instance = manager.get_instance(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"浏览器实例不存在: {instance_id}",
        )

    return BrowserHealthResponse(
        instance_id=instance_id,
        is_connected=instance.is_connected,
        mode=instance.mode.value,
    )


@router.post(
    "/{instance_id}/set-default",
    summary="设置默认实例",
    description="设置默认浏览器实例",
)
async def set_default_browser(instance_id: str):
    """
    设置默认浏览器实例

    - **instance_id**: 浏览器实例 ID
    """
    from src.adapters.browser import get_browser_manager

    manager = get_browser_manager()
    success = manager.set_default_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"浏览器实例不存在: {instance_id}",
        )

    return {"message": "已设置为默认实例", "instance_id": instance_id}

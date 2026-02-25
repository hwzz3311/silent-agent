"""
执行相关 API 路由

提供工具调用和执行管理的接口。
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, status

from src.api.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    BatchExecuteRequest,
    BatchExecuteResponse,
    FlowExecuteRequest,
    FlowExecuteResponse,
    ExecutionStatus,
    ErrorResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 工具执行 ====================

@router.post(
    "",
    response_model=ExecuteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
    summary="执行工具调用",
    description="执行指定的工具调用并返回结果",
)
async def execute_tool(request: ExecuteRequest):
    """
    执行单个工具调用

    请求体:
    - **tool**: 工具名称
    - **params**: 工具参数
    - **timeout**: 可选的超时时间（毫秒）
    - **tab_id**: 可选的标签页 ID
    """
    # 获取客户端
    from src.api.app import get_client

    # 记录请求日志
    logger.info(f"[API] 收到工具执行请求: tool={request.tool}")
    logger.debug(f"[API] 请求参数: {json.dumps(request.params or {}, ensure_ascii=False, indent=2)}")

    client = await get_client()

    if not client.is_connected:
        logger.warning("[API] 浏览器扩展未连接")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="浏览器扩展未连接",
        )

    try:
        # 创建 ExecutionContext 并传入 tab_id、client 和 secret_key
        from src.tools.base import ExecutionContext
        context = ExecutionContext(
            tab_id=request.tab_id,
            client=client,
            secret_key=request.secret_key  # 传递密钥用于多插件路由
        )

        # 执行工具调用
        logger.info(f"[API] 开始执行工具: {request.tool}, tab_id={request.tab_id}, secret_key={request.secret_key}")
        result = await client.execute_tool(
            name=request.tool,
            params=request.params or {},
            timeout=(request.timeout or 60000) / 1000,
            context=context,
            secret_key=request.secret_key,  # 传递密钥用于多插件路由
        )
        logger.debug(f"[API] 工具执行结果: {json.dumps(result, ensure_ascii=False, default=str)}")
        # 记录响应日志
        success = result.get("success", False)
        logger.info(f"[API] 工具执行完成: tool={request.tool}, success={success}")
        logger.debug(f"[API] 响应数据: {json.dumps(result.get('data') if result else {}, ensure_ascii=False, default=str)}")

        if not success and result.get("error"):
            logger.error(f"[API] 工具执行错误: {json.dumps(result.get('error'), ensure_ascii=False, default=str)}")

        return ExecuteResponse(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            meta={
                "tool": request.tool,
                "duration_ms": result.get("duration_ms", 0),
            },
        )

    except Exception as e:
        # 记录详细错误日志
        logger.error(f"[API] 工具执行异常: tool={request.tool}, error={str(e)}")
        logger.error(f"[API] 异常详情:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行失败: {str(e)}",
        )


@router.post(
    "/batch",
    response_model=BatchExecuteResponse,
    summary="批量执行工具调用",
    description="批量执行多个工具调用，支持顺序和并行执行",
)
async def execute_batch(request: BatchExecuteRequest):
    """
    批量执行工具调用

    请求体:
    - **calls**: 工具调用列表
    - **continue_on_error**: 遇到错误时是否继续执行
    - **parallel**: 是否并行执行
    """
    from src.api.app import get_client

    client = await get_client()

    if not client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="浏览器扩展未连接",
        )

    results = []
    success_count = 0
    failure_count = 0
    start_time = datetime.utcnow()

    for call in request.calls:
        try:
            result = await client.execute_tool(
                name=call.name,
                params=call.params or {},
            )

            is_success = result.get("success", False)
            results.append(ExecuteResponse(
                success=is_success,
                data=result.get("data"),
                error=result.get("error"),
            ))

            if is_success:
                success_count += 1
            else:
                failure_count += 1
                if not request.continue_on_error:
                    break

        except Exception as e:
            results.append(ExecuteResponse(
                success=False,
                error={"message": str(e)},
            ))
            failure_count += 1
            if not request.continue_on_error:
                break

    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    return BatchExecuteResponse(
        results=results,
        success_count=success_count,
        failure_count=failure_count,
        total_duration_ms=int(duration_ms),
    )


@router.post(
    "/flow",
    response_model=FlowExecuteResponse,
    summary="执行流程",
    description="执行预定义的流程",
)
async def execute_flow(request: FlowExecuteRequest):
    """
    执行流程

    请求体:
    - **flow_id**: 流程 ID
    - **flow_data**: 流程数据（直接提供流程定义）
    - **variables**: 初始变量
    - **timeout**: 总超时时间

    注意: 此接口待流程引擎实现后完善
    """
    # TODO: 实现流程引擎后完善
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="流程执行功能待实现",
    )


@router.get(
    "/{execution_id}",
    summary="查询执行状态",
    description="根据执行 ID 查询执行状态和结果",
)
async def get_execution_status(execution_id: str):
    """
    查询执行状态

    - **execution_id**: 执行 ID

    返回执行的当前状态和结果。
    """
    # TODO: 实现执行状态追踪后完善
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="执行状态查询功能待实现",
    )


@router.delete(
    "/{execution_id}",
    summary="终止执行",
    description="终止正在执行的流程",
)
async def terminate_execution(execution_id: str):
    """
    终止执行

    - **execution_id**: 执行 ID

    终止指定的执行并返回结果。
    """
    # TODO: 实现执行终止功能后完善
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="执行终止功能待实现",
    )
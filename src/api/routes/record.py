"""
录制回放相关 API 路由

提供录制开始/停止、回放等接口。
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import (
    RecordStartResponse,
    RecordStopResponse,
    RecordDetailResponse,
    RecordListResponse,
    ReplayRequest,
    ReplayResponse,
    ErrorResponse,
)
from src.recorder import RecordingStorage

router = APIRouter()


# ==================== 录制接口 ====================

@router.post(
    "/start",
    response_model=RecordStartResponse,
    summary="开始录制",
    description="开始录制用户操作序列",
)
async def start_recording(
    tab_id: Optional[str] = Query(None, description="指定标签页ID，默认当前激活标签页"),
):
    """
    开始录制用户操作

    返回录制ID和相关信息。
    """
    from src.api.app import get_client

    client = await get_client()

    if not client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="浏览器扩展未连接",
        )

    try:
        result = await client.execute_tool(
            name="recorder_start",
            params={"tabId": tab_id} if tab_id else {},
        )

        return RecordStartResponse(
            recording_id=result.get("recordingId"),
            started_at=result.get("startedAt"),
            tab_id=result.get("tabId"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"开始录制失败: {str(e)}",
        )


@router.post(
    "/{recording_id}/stop",
    response_model=RecordStopResponse,
    summary="停止录制",
    description="停止当前录制并返回录制结果",
)
async def stop_recording(recording_id: str):
    """
    停止录制

    - **recording_id**: 录制ID

    返回录制结果，包括操作序列。
    """
    from src.api.app import get_client

    client = await get_client()

    if not client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="浏览器扩展未连接",
        )

    try:
        result = await client.execute_tool(
            name="recorder_stop",
            params={"recordingId": recording_id},
        )

        return RecordStopResponse(
            recording_id=recording_id,
            stopped_at=result.get("stoppedAt"),
            actions_count=result.get("actionsCount"),
            duration_ms=result.get("durationMs"),
            page_url=result.get("pageUrl"),
            page_title=result.get("pageTitle"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止录制失败: {str(e)}",
        )


# ==================== 录制查询接口 ====================

@router.get(
    "",
    response_model=RecordListResponse,
    summary="获取录制列表",
    description="获取所有录制记录的列表",
)
async def list_recordings(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取录制列表

    返回录制记录的简要信息列表。
    """
    from src.recorder.storage import RecordingStorage

    storage = RecordingStorage()
    recordings = storage.list_recordings(page=page, page_size=page_size)

    return RecordListResponse(
        recordings=recordings.get("recordings", []),
        total=recordings.get("total", 0),
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{recording_id}",
    response_model=RecordDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "录制不存在"},
    },
    summary="获取录制详情",
    description="获取指定录制的完整操作序列",
)
async def get_recording(recording_id: str):
    """
    获取录制详情

    - **recording_id**: 录制ID

    返回录制的完整信息，包括所有操作步骤。
    """
    from src.recorder.storage import RecordingStorage

    storage = RecordingStorage()
    recording = storage.get_recording(recording_id)

    if not recording:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"录制不存在: {recording_id}",
        )

    return RecordDetailResponse(
        id=recording.id,
        name=recording.name,
        description=recording.description,
        created_at=recording.created_at.isoformat(),
        duration_ms=recording.duration_ms,
        actions=recording.actions,
        page_url=recording.page_url,
        page_title=recording.page_title,
    )


# ==================== 回放接口 ====================

@router.post(
    "/{recording_id}/replay",
    response_model=ReplayResponse,
    summary="回放录制",
    description="开始回放指定的录制",
)
async def replay_recording(
    recording_id: str,
    request: ReplayRequest = None,
):
    """
    回放录制

    - **recording_id**: 录制ID
    - **speed**: 回放速度 (default: 1.0)
    - **headless**: 是否 headless 模式执行

    返回执行ID和相关信息。
    """
    from src.api.app import get_client
    from src.recorder.player import RecordingPlayer

    client = await get_client()

    if not client.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="浏览器扩展未连接",
        )

    speed = request.speed if request else 1.0
    headless = request.headless if request else False

    try:
        # 加载录制
        storage = RecordingStorage()
        recording = storage.get_recording(recording_id)

        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"录制不存在: {recording_id}",
            )

        # 创建回放器并执行
        player = RecordingPlayer(client, recording)

        # 执行回放
        execution_id = await player.playback(
            speed=speed,
            headless=headless,
        )

        return ReplayResponse(
            execution_id=execution_id,
            recording_id=recording_id,
            status="started",
            speed=speed,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回放失败: {str(e)}",
        )


@router.get(
    "/{recording_id}/replay/{execution_id}/status",
    summary="查询回放状态",
    description="查询回放执行的当前状态",
)
async def get_replay_status(recording_id: str, execution_id: str):
    """
    查询回放状态

    返回回放执行的当前状态和进度。
    """
    from src.recorder.player import RecordingPlayer

    try:
        status_info = await RecordingPlayer.get_status(execution_id)

        return {
            "execution_id": execution_id,
            "recording_id": recording_id,
            **status_info,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询状态失败: {str(e)}",
        )


@router.post(
    "/{recording_id}/replay/{execution_id}/stop",
    summary="停止回放",
    description="停止正在进行的回放",
)
async def stop_replay(recording_id: str, execution_id: str):
    """
    停止回放

    - **recording_id**: 录制ID
    - **execution_id**: 执行ID

    停止回放并返回结果。
    """
    from src.recorder.player import RecordingPlayer

    try:
        await RecordingPlayer.stop(execution_id)

        return {
            "execution_id": execution_id,
            "status": "stopped",
            "message": "回放已停止",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止回放失败: {str(e)}",
        )


# ==================== 录制优化接口 ====================

@router.post(
    "/{recording_id}/optimize",
    summary="AI优化录制",
    description="使用AI优化录制操作序列",
)
async def optimize_recording(
    recording_id: str,
    instructions: str = Query(..., description="优化指令"),
):
    """
    AI优化录制

    - **recording_id**: 录制ID
    - **instructions**: 优化指令

    返回优化后的录制信息。
    """
    from src.recorder.optimizer import RecordingOptimizer

    try:
        optimizer = RecordingOptimizer()
        result = await optimizer.optimize(recording_id, instructions)

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"优化失败: {str(e)}",
        )
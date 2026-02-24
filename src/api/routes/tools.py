"""
工具相关 API 路由

提供工具列表、搜索、详情等接口。
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query, status

from src.api.schemas import (
    ToolListResponse,
    ToolDetailResponse,
    ToolSchemaResponse,
    ToolSearchResponse,
)


router = APIRouter()


@router.get(
    "",
    response_model=ToolListResponse,
    summary="获取工具列表",
    description="获取所有可用工具的名称列表",
)
async def list_tools():
    """
    获取所有可用工具

    返回工具名称列表、分类统计等信息。
    """
    from src.tools import list_tools as get_tool_list, get_registry

    tool_names = get_tool_list()
    registry = get_registry()
    stats = registry.get_stats()

    return ToolListResponse(
        tools=tool_names,
        count=len(tool_names),
        categories=stats.get("categories", {}),
        tags=stats.get("tags", {}),
    )


@router.get(
    "/search",
    response_model=ToolSearchResponse,
    summary="搜索工具",
    description="根据关键词搜索工具",
)
async def search_tools(q: str = Query(..., min_length=1, description="搜索关键词")):
    """
    搜索工具

    - **q**: 搜索关键词

    返回匹配的工具名称列表。
    """
    from src.tools import search_tools as search

    results = search(q)

    return ToolSearchResponse(
        query=q,
        results=results,
        count=len(results),
    )


@router.get(
    "/{name}",
    response_model=ToolDetailResponse,
    responses={
        404: {"description": "工具不存在"},
    },
    summary="获取工具详情",
    description="获取指定工具的详细信息和参数说明",
)
async def get_tool(name: str):
    """
    获取工具详情

    - **name**: 工具名称

    返回工具的完整信息，包括参数说明、返回值类型等。
    """
    from src.tools import get_tool as get_tool_func

    tool = get_tool_func(name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具不存在: {name}",
        )

    info = tool.get_info()

    return ToolDetailResponse(
        name=info.name,
        description=info.description,
        version=info.version,
        category=info.category,
        tags=info.tags,
        parameters=tool.get_parameters_schema(),
        returns=tool.get_returns_schema(),
    )


@router.get(
    "/{name}/schema",
    response_model=ToolSchemaResponse,
    responses={
        404: {"description": "工具不存在"},
    },
    summary="获取工具参数 Schema",
    description="获取指定工具的 JSON Schema 用于参数验证",
)
async def get_tool_schema(name: str):
    """
    获取工具参数 Schema

    - **name**: 工具名称

    返回工具参数的 JSON Schema，可用于客户端验证。
    """
    from src.tools import get_tool as get_tool_func

    tool = get_tool_func(name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具不存在: {name}",
        )

    return ToolSchemaResponse(
        name=tool.name,
        description=tool.description,
        version=tool.version,
        parameters=tool.get_parameters_schema(),
        returns=tool.get_returns_schema(),
    )


@router.get(
    "/{name}/versions",
    summary="获取工具版本历史",
    description="获取工具的版本历史记录",
)
async def get_tool_versions(name: str):
    """
    获取工具版本历史

    - **name**: 工具名称

    返回工具的版本历史记录。
    """
    from src.tools import get_registry

    registry = get_registry()
    if not registry.exists(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具不存在: {name}",
        )

    versions = registry.get_version_history(name)

    return {
        "tool": name,
        "versions": [
            {
                "version": v.version,
                "released_at": v.released_at.isoformat(),
                "changelog": v.changelog,
            }
            for v in versions
        ],
    }
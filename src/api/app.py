"""
FastAPI 应用模块

提供 Neurone RPA Server 的 API 入口。
支持多种浏览器客户端模式：extension/puppeteer/hybrid
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.api.schemas import (
    ExecuteRequest,
    FlowExecuteRequest,
    ErrorResponse,
    HealthResponse,
    ServerInfo,
)
from src.api.routes import tools, execute, flows

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局客户端实例（统一浏览器客户端）
_browser_client = None


async def get_client():
    """获取全局浏览器客户端实例（统一接口）"""
    global _browser_client
    if _browser_client is None:
        from src.browser import BrowserClientFactory, BrowserMode
        from src.config import get_config

        config = get_config()
        mode = config.browser.mode

        logger.info(f"创建浏览器客户端，模式: {mode.value}")

        if mode == BrowserMode.EXTENSION:
            # 使用旧的客户端（向后兼容）
            from src.client.client import SilentAgentClient
            _browser_client = SilentAgentClient()
            try:
                await _browser_client.connect()
            except Exception as e:
                logger.warning(f"无法连接到扩展: {e}")
        else:
            # 使用新的统一客户端
            _browser_client = BrowserClientFactory.create_client(mode)
            try:
                await _browser_client.connect()
                logger.info(f"浏览器客户端已连接 (模式: {mode.value})")
            except Exception as e:
                logger.warning(f"浏览器客户端连接失败: {e}")

    return _browser_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    from src.config import get_config
    config = get_config()

    logger.info(f"Neurone RPA Server 启动中... 浏览器模式: {config.browser.mode.value}")
    try:
        client = await get_client()
        # 检查连接状态
        is_connected = getattr(client, 'is_connected', lambda: False)()
        logger.info(f"客户端状态: {is_connected}")
    except Exception as e:
        logger.warning(f"客户端初始化失败: {e}")

    yield

    # 关闭时
    logger.info("Neurone RPA Server 关闭中...")
    global _browser_client
    if _browser_client:
        try:
            await _browser_client.close()
        except Exception as e:
            logger.warning(f"客户端关闭失败: {e}")
    _browser_client = None


# 创建 FastAPI 应用
app = FastAPI(
    title="Neurone RPA Server",
    description="浏览器智能代理控制系统 - 通过工具调用实现远程浏览器自动化",
    version="2.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tools.router, prefix="/api/v1/tools", tags=["Tools"])
app.include_router(execute.router, prefix="/api/v1/execute", tags=["Execute"])
app.include_router(flows.router, prefix="/api/v1/flows", tags=["Flows"])


# ==================== 根路径 ====================

@app.get("/", response_model=ServerInfo)
async def root():
    """获取服务器信息"""
    from src.tools import list_tools

    return ServerInfo(
        version="2.0.0",
        host="127.0.0.1",
        port=8080,
        tools_count=len(list_tools()),
        flows_count=0,  # TODO: 实现流程存储后更新
    )


# ==================== 健康检查 ====================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    client = await get_client()
    return HealthResponse(
        status="healthy" if client.is_connected else "degraded",
        version="2.0.0",
        extensions=["chrome-extension"] if client.is_connected else [],
    )


# ==================== 工具执行接口 (T2.5.3) ====================

@app.post(
    "/api/v1/execute",
    response_model=execute.ExecuteResponse,
    responses={
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
    summary="执行单个工具调用",
    description="执行指定的工具调用并返回结果",
)
async def execute_tool(request: ExecuteRequest):
    """
    执行单个工具调用

    - **tool**: 工具名称 (如 `browser.click`)
    - **params**: 工具参数
    - **timeout**: 可选的超时时间（毫秒）
    - **tab_id**: 可选的标签页 ID
    """
    try:
        client = await get_client()

        if not client.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="扩展未连接",
            )

        # 执行工具调用
        result = await client.execute_tool(
            request.tool,
            request.params,
            timeout=(request.timeout or 60000) / 1000,  # 转换为秒
        )

        return execute.ExecuteResponse(
            success=result.get("success", False),
            data=result.get("data"),
            error=result.get("error"),
            meta={
                "tool": request.tool,
                "duration_ms": result.get("duration_ms", 0),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"工具执行失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行失败: {str(e)}",
        )


@app.post(
    "/api/v1/execute/batch",
    response_model=execute.BatchExecuteResponse,
    summary="批量执行工具调用",
    description="批量执行多个工具调用，支持顺序和并行执行",
)
async def execute_batch(request: execute.BatchExecuteRequest):
    """
    批量执行工具调用

    - **calls**: 工具调用列表
    - **continue_on_error**: 遇到错误时是否继续
    - **parallel**: 是否并行执行
    """
    try:
        client = await get_client()

        if not client.is_connected:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="扩展未连接",
            )

        results = []
        success_count = 0
        failure_count = 0
        start_time = datetime.utcnow()

        for call in request.calls:
            try:
                result = await client.execute_tool(call.name, call.params or {})
                is_success = result.get("success", False)

                results.append(execute.ExecuteResponse(
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
                results.append(execute.ExecuteResponse(
                    success=False,
                    error={"message": str(e)},
                ))
                failure_count += 1
                if not request.continue_on_error:
                    break

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return execute.BatchExecuteResponse(
            results=results,
            success_count=success_count,
            failure_count=failure_count,
            total_duration_ms=int(duration_ms),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量执行失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量执行失败: {str(e)}",
        )


@app.post(
    "/api/v1/execute/flow",
    response_model=execute.FlowExecuteResponse,
    summary="执行流程",
    description="执行预定义的流程",
)
async def execute_flow(request: FlowExecuteRequest):
    """
    执行流程

    - **flow_id**: 流程 ID
    - **flow_data**: 流程数据（直接提供流程定义）
    - **variables**: 初始变量
    - **timeout**: 总超时时间
    """
    # TODO: 实现流程引擎后完善
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="流程执行功能待实现",
    )


# ==================== 工具列表接口 (T2.5.4) ====================

@app.get(
    "/api/v1/tools",
    response_model=tools.ToolListResponse,
    summary="获取工具列表",
    description="获取所有可用工具的名称列表",
)
async def list_tools():
    """获取所有可用工具"""
    from src.tools import list_tools as get_tool_list

    tool_names = get_tool_list()

    return tools.ToolListResponse(
        tools=tool_names,
        count=len(tool_names),
        categories={"browser": 11, "utility": 1},  # TODO: 动态计算
        tags={},
    )


@app.get(
    "/api/v1/tools/{name}",
    response_model=tools.ToolDetailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "工具不存在"},
    },
    summary="获取工具详情",
    description="获取指定工具的详细信息和参数说明",
)
async def get_tool_detail(name: str):
    """
    获取工具详情

    - **name**: 工具名称
    """
    from src.tools import get_tool

    tool = get_tool(name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具不存在: {name}",
        )

    info = tool.get_info()

    return tools.ToolDetailResponse(
        name=info.name,
        description=info.description,
        version=info.version,
        category=info.category,
        tags=info.tags,
        parameters=tool.get_parameters_schema(),
        returns=tool.get_returns_schema(),
    )


@app.get(
    "/api/v1/tools/{name}/schema",
    response_model=tools.ToolSchemaResponse,
    responses={
        404: {"model": ErrorResponse, "description": "工具不存在"},
    },
    summary="获取工具参数 Schema",
    description="获取指定工具的 JSON Schema",
)
async def get_tool_schema(name: str):
    """
    获取工具参数 Schema

    - **name**: 工具名称
    """
    from src.tools import get_tool

    tool = get_tool(name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工具不存在: {name}",
        )

    return tools.ToolSchemaResponse(
        name=tool.name,
        description=tool.description,
        version=tool.version,
        parameters=tool.get_parameters_schema(),
        returns=tool.get_returns_schema(),
    )


# ==================== 错误处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": "服务器内部错误",
            "details": {"type": type(exc).__name__},
        },
    )


# ==================== 启动 ====================

def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
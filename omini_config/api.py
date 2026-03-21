"""
OminiConfig API - FastAPI 路由挂载示例
"""

from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from adapter import (
    JsonConfigAdapter,
    IOminiConfigAdapter,
    ConfigException,
    ConcurrencyConflictException,
    ConfigNotFoundException,
    ConfigFormatException,
)


# Pydantic 模型定义
class ConfigResponse(BaseModel):
    """配置读取响应"""

    data: Dict[str, Any]
    meta: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "data": {"setting1": "value1", "setting2": 42},
                "meta": {"versionHash": "abc123...", "lastModified": 1711000000.0},
            }
        }


class SaveConfigRequest(BaseModel):
    """保存配置请求"""

    data: Dict[str, Any]
    oldVersionHash: str

    class Config:
        json_schema_extra = {
            "example": {
                "data": {"setting1": "new_value", "setting2": 100},
                "oldVersionHash": "abc123...",
            }
        }


class SaveConfigResponse(BaseModel):
    """保存配置响应"""

    success: bool
    newVersionHash: str

    class Config:
        json_schema_extra = {
            "example": {"success": True, "newVersionHash": "def456..."}
        }


class SchemaResponse(BaseModel):
    """Schema 响应"""

    schema_def: Dict[str, Any] = Field(..., alias="schema")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "schema": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "properties": {
                        "setting1": {"type": "string"},
                        "setting2": {"type": "number"},
                    },
                    "required": ["setting1", "setting2"],
                }
            }
        }


class ErrorResponse(BaseModel):
    """错误响应"""

    detail: str
    error_type: str

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "配置冲突: 期望哈希与实际不匹配",
                "error_type": "ConcurrencyConflictException",
            }
        }


# 依赖注入：创建适配器实例
def get_config_adapter() -> IOminiConfigAdapter:
    """
    创建配置适配器实例

    在实际生产环境中，可以使用依赖注入框架（如 dependency-injector）
    或从配置中读取 base_dir
    """
    return JsonConfigAdapter(base_dir="./configs")


# 异常转换中间件
async def config_exception_handler(request, exc: Exception):
    """将配置异常转换为 HTTP 响应"""
    if isinstance(exc, ConcurrencyConflictException):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Concurrency conflict",
                "message": str(exc),
                "expected_hash": exc.expected_hash,
                "actual_hash": exc.actual_hash,
                "error_type": "ConcurrencyConflictException",
            },
        )
    elif isinstance(exc, ConfigNotFoundException):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Config not found",
                "message": str(exc),
                "error_type": "ConfigNotFoundException",
            },
        )
    elif isinstance(exc, ConfigFormatException):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Config format error",
                "message": str(exc),
                "error_type": "ConfigFormatException",
            },
        )
    elif isinstance(exc, ConfigException):
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Config error",
                "message": str(exc),
                "error_type": type(exc).__name__,
            },
        )
    else:
        # 未知异常，重新抛出
        raise


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    app = FastAPI(
        title="OminiConfig API",
        description="轻量级通用配置管理器 - JSON 适配器 HTTP 接口",
        version="1.0.0",
    )

    # CORS 中间件（允许前端跨域访问）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制为具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册异常处理器
    app.add_exception_handler(ConfigException, config_exception_handler)

    return app


# 创建应用实例
app = create_app()


@app.get(
    "/api/config/{source_path:path}",
    response_model=ConfigResponse,
    summary="读取配置",
    description="读取指定路径的配置文件内容及其元数据（versionHash 和 lastModified）",
    responses={
        200: {"description": "成功返回配置数据"},
        404: {"description": "配置文件不存在", "model": ErrorResponse},
        422: {"description": "配置文件格式错误", "model": ErrorResponse},
    },
)
async def read_config(
    source_path: str, adapter: IOminiConfigAdapter = Depends(get_config_adapter)
) -> Dict[str, Any]:
    """
    读取配置文件

    - **source_path**: 配置文件路径（相对于 base_dir）
    - 如果文件不存在，会自动初始化空配置
    """
    result = adapter.read_config(source_path)
    return result.to_dict()


@app.post(
    "/api/config/{source_path:path}",
    response_model=SaveConfigResponse,
    summary="保存配置",
    description="保存配置数据到指定路径，必须提供 oldVersionHash 进行并发冲突校验",
    responses={
        200: {"description": "配置保存成功"},
        409: {
            "description": "并发冲突 - 配置已被其他客户端修改",
            "model": ErrorResponse,
        },
        422: {"description": "请求格式错误或数据类型不匹配", "model": ErrorResponse},
    },
)
async def write_config(
    source_path: str,
    request: SaveConfigRequest,
    adapter: IOminiConfigAdapter = Depends(get_config_adapter),
) -> Dict[str, Any]:
    """
    保存配置

    - **source_path**: 配置文件路径（相对于 base_dir）
    - **request.data**: 要保存的配置数据
    - **request.oldVersionHash**: 读取时获取的版本哈希

    **并发控制说明**:
    - 如果 oldVersionHash 与服务器端当前文件的哈希不匹配，返回 409 冲突错误
    - 写入成功后会返回新的 versionHash
    """
    # 执行写入
    adapter.write_config(
        source_path=source_path,
        data=request.data,
        old_version_hash=request.oldVersionHash,
    )

    # 重新读取以获取新的 versionHash
    result = adapter.read_config(source_path)

    return {"success": True, "newVersionHash": result.meta.version_hash}


@app.get(
    "/api/schema/{source_path:path}",
    response_model=SchemaResponse,
    summary="获取配置 Schema",
    description="根据当前配置数据自动推导 JSON Schema 结构，供前端动态渲染 GUI",
    responses={
        200: {"description": "成功返回 Schema 定义"},
        404: {"description": "配置文件不存在", "model": ErrorResponse},
        422: {"description": "配置文件格式错误", "model": ErrorResponse},
    },
)
async def generate_schema(
    source_path: str, adapter: IOminiConfigAdapter = Depends(get_config_adapter)
) -> Dict[str, Any]:
    """
    生成 JSON Schema

    - **source_path**: 配置文件路径（相对于 base_dir）
    - 根据配置的实际数据类型自动推导 Schema 结构
    - 支持嵌套对象、数组等复杂类型
    """
    schema = adapter.generate_schema(source_path)
    return {"schema": schema}


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "OminiConfig API"}


if __name__ == "__main__":
    import uvicorn

    # 开发服务器启动
    print("🚀 启动 OminiConfig API 服务...")
    print("📖 API 文档: http://localhost:8000/docs")
    print("📚 替代文档: http://localhost:8000/redoc")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")

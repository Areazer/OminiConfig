"""
main.py

OminiConfig 企业级后端服务入口

重构亮点：
1. 安全加固：路径沙箱校验防止目录穿越攻击
2. 架构升级：工厂模式支持多格式适配器（JSON/YAML/...）
3. 并发安全：跨平台原子写入（os.replace）+ 乐观锁
4. 实时推送：SSE 接口支持文件变更热更新

启动命令：
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

API 文档：
    Swagger UI: http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc
"""

import sys
from pathlib import Path

# 确保能导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.router import router, WORKSPACE_DIR


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例

    Returns:
        FastAPI: 配置完成的应用实例
    """
    app = FastAPI(
        title="OminiConfig Enterprise",
        description=(
            "企业级通用配置管理器后端服务\n\n"
            "核心特性：\n"
            "- 🔒 路径沙箱：严格限制在 WORKSPACE_DIR 内，防御路径穿越攻击\n"
            "- 🏭 工厂模式：支持多格式适配器（JSON/YAML/...），易于扩展\n"
            "- ⚡ 原子写入：跨平台安全的文件写入（tempfile + os.replace）\n"
            "- 🔄 乐观锁：SHA256 版本哈希防止并发冲突\n"
            "- 📡 实时推送：SSE 接口支持文件变更热更新\n"
        ),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS 中间件配置
    # 生产环境应限制为具体域名，而非通配符 *
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册 API 路由
    app.include_router(router)

    # 挂载静态文件目录
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # 根路径返回前端页面
    @app.get("/")
    async def root():
        return FileResponse("static/index.html")

    # 启动时确保工作目录存在
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    return app


# 创建应用实例（供 uvicorn 使用）
app = create_app()


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 OminiConfig Enterprise 启动中...")
    print("=" * 60)
    print(f"📁 工作目录: {WORKSPACE_DIR}")
    print(f"🖥️  GUI 界面: http://localhost:8000")
    print(f"📖 API 文档: http://localhost:8000/docs")
    print(f"📚 备用文档: http://localhost:8000/redoc")
    print("=" * 60)

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os

from app.config import settings
from app.models import init_db
from app.routes import (
    sources_router,
    articles_router,
    keywords_router,
    system_router
)
from app.services import scheduler
from app.core.logging import setup_logging, get_logger

# 初始化日志系统
setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)

# 静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class NoCacheStaticFiles(StaticFiles):
    """禁用缓存的静态文件服务"""
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    使用新的 lifespan API 替代弃用的 on_event
    """
    # === Startup ===
    logger.info("应用启动中...")
    
    # 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")
    
    # 启动定时任务调度器
    scheduler.start()
    logger.info("定时任务调度器已启动")
    
    logger.info("应用启动完成")
    
    yield  # 应用运行中
    
    # === Shutdown ===
    logger.info("应用关闭中...")
    
    # 停止调度器
    scheduler.stop()
    logger.info("定时任务调度器已停止")
    
    logger.info("应用已关闭")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Returns:
        配置好的 FastAPI 应用
    """
    # 创建应用，使用新的 lifespan API
    app = FastAPI(
        title="Briefly API",
        description="Briefly RSS 阅读器后端 API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # 配置 CORS - 从环境变量读取允许的域名
    allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
    )
    
    # 挂载静态文件（禁用缓存）
    app.mount("/static", NoCacheStaticFiles(directory=STATIC_DIR), name="static")
    logger.info(f"静态文件挂载完成: {STATIC_DIR}")
    
    # 注册路由
    app.include_router(sources_router)
    app.include_router(articles_router)
    app.include_router(keywords_router)
    app.include_router(system_router)
    logger.info("路由注册完成")
    
    # 根路径重定向到前端首页
    @app.get("/")
    async def root():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
    
    # 阅读页面
    @app.get("/index.html")
    async def index_page():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
    
    # 配置页面
    @app.get("/config.html")
    async def config_page():
        return FileResponse(os.path.join(STATIC_DIR, "config.html"))
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

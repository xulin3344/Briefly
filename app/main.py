from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
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

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Returns:
        配置好的 FastAPI 应用
    """
    # 创建应用
    app = FastAPI(
        title="Briefly API",
        description="Briefly RSS 阅读器后端 API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 挂载静态文件（禁用缓存）
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", NoCacheStaticFiles(directory=static_dir), name="static")
    logger.info(f"静态文件挂载完成: {static_dir}")
    
    # 注册路由
    app.include_router(sources_router)
    app.include_router(articles_router)
    app.include_router(keywords_router)
    app.include_router(system_router)
    logger.info("路由注册完成")
    
    # 启动事件：启动调度器
    @app.on_event("startup")
    async def startup_event():
        logger.info("应用启动中...")
        
        # 初始化数据库（测试模式下跳过）
        import os
        if os.environ.get("TESTING") != "1":
            await init_db()
            logger.info("数据库初始化完成")
        
        # 启动定时任务调度器
        scheduler.start()
        logger.info("定时任务调度器已启动")
        
        logger.info("应用启动完成")
    
    # 关闭事件：停止调度器
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("应用关闭中...")
        
        # 停止调度器
        scheduler.stop()
        logger.info("定时任务调度器已停止")
        
        logger.info("应用已关闭")
    
    # 根路径重定向到前端首页
    @app.get("/")
    async def root():
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    # 阅读页面
    @app.get("/index.html")
    async def index_page():
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    # 配置页面
    @app.get("/config.html")
    async def config_page():
        return FileResponse(os.path.join(static_dir, "config.html"))
    
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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import get_db, RSSSource, Article, KeywordConfig
from app.services import (
    scheduler,
    ai_service,
    webhook_service,
    rss_service,
    keyword_service
)

router = APIRouter(prefix="/api", tags=["系统管理"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    健康检查接口
    
    Returns:
        服务状态
    """
    return {
        "status": "healthy",
        "service": "Briefly",
        "version": "1.0.0",
        "database": "connected"
    }


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    """
    获取系统状态
    
    Returns:
        系统状态字典
    """
    from app.models import WebhookConfig
    from sqlalchemy import select
    
    # 获取 RSS 源统计
    sources_result = await db.execute(select(RSSSource))
    sources = sources_result.scalars().all()
    
    enabled_sources = sum(1 for s in sources if s.enabled)
    total_sources = len(sources)
    
    # 获取文章统计
    articles_result = await db.execute(
        select(func.count(Article.id)).where(Article.is_filtered == False)
    )
    total_articles = articles_result.scalar() or 0
    
    # 获取过滤文章统计
    filtered_result = await db.execute(
        select(func.count(Article.id)).where(Article.is_filtered == True)
    )
    filtered_articles = filtered_result.scalar() or 0
    
    # 获取关键词统计
    keywords_result = await db.execute(select(KeywordConfig))
    keywords = keywords_result.scalars().all()
    
    enabled_keywords = sum(1 for k in keywords if k.enabled)
    total_keywords = len(keywords)
    
    # 获取调度器状态
    scheduler_status = scheduler.get_status()
    
    # 获取 Webhook 配置状态
    webhook_result = await db.execute(select(WebhookConfig).where(WebhookConfig.id == 1))
    webhook_config = webhook_result.scalar_one_or_none()
    webhook_enabled = bool(webhook_config and webhook_config.enabled and webhook_config.url)
    
    return {
        "database": {
            "enabled_sources": enabled_sources,
            "total_sources": total_sources,
            "total_articles": total_articles,
            "filtered_articles": filtered_articles,
            "total_keywords": total_keywords,
            "enabled_keywords": enabled_keywords
        },
        "scheduler": scheduler_status,
        "ai_configured": bool(ai_service.get_openai_client() is not None),
        "webhook_enabled": webhook_enabled
    }


@router.post("/fetch")
def trigger_fetch():
    """
    手动触发 RSS 抓取任务（同步执行，等待完成）
    
    Returns:
        任务执行结果
    """
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(scheduler.fetch_rss_task())
        return result
    finally:
        loop.close()


@router.post("/fetch/start")
def start_fetch_background():
    """
    后台触发 RSS 抓取任务（立即返回，后台执行）
    
    Returns:
        启动状态
    """
    import threading
    
    def run_fetch():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(scheduler.fetch_rss_task())
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_fetch, daemon=True)
    thread.start()
    
    return {
        "status": "started",
        "message": "RSS 抓取任务已在后台启动"
    }


@router.post("/summarize")
def trigger_summarize():
    """
    手动触发 AI 总结任务
    
    Returns:
        任务执行结果
    """
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(scheduler.ai_summary_task())
        return result
    finally:
        loop.close()


@router.post("/run-pipeline")
def run_full_pipeline():
    """
    运行完整处理流程：抓取 -> 过滤 -> 总结
    
    Returns:
        流程执行结果
    """
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(scheduler.run_full_pipeline())
        return result
    finally:
        loop.close()


@router.post("/test/rss")
async def test_rss_fetch(url: str):
    """
    测试 RSS 源连接
    
    Args:
        url: RSS 源 URL
        
    Returns:
        测试结果
    """
    result = await rss_service.test_rss_connection(url)
    return result


@router.post("/test/webhook")
def test_webhook():
    """
    测试 Webhook 连接
    
    Returns:
        测试结果
    """
    result = webhook_service.test_webhook_connection()
    return result


@router.post("/scheduler/start")
def start_scheduler():
    """
    启动定时任务调度器
    
    Returns:
        启动结果
    """
    if scheduler._is_running:
        return {
            "success": False,
            "message": "调度器已在运行"
        }
    
    scheduler.start()
    return {
        "success": True,
        "message": "调度器已启动"
    }


@router.post("/scheduler/stop")
def stop_scheduler():
    """
    停止定时任务调度器
    
    Returns:
        停止结果
    """
    if not scheduler._is_running:
        return {
            "success": False,
            "message": "调度器未运行"
        }
    
    scheduler.stop()
    return {
        "success": True,
        "message": "调度器已停止"
    }


class AISettingsUpdate(BaseModel):
    api_key: str = None
    base_url: str = None
    model: str = None
    max_summary_length: int = None
    enabled: bool = None


@router.get("/ai/config")
async def get_ai_config(db: AsyncSession = Depends(get_db)):
    """
    获取当前 AI 配置
    
    Returns:
        AI 配置信息（不包含 API Key）
    """
    config = await ai_service.get_ai_config(db)
    return config


@router.post("/ai/settings")
async def save_ai_settings(
    settings: AISettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    保存 AI 设置
    
    Args:
        settings: AI 设置更新
        db: 数据库会话
        
    Returns:
        保存结果
    """
    await ai_service.save_ai_settings(
        db,
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
        max_summary_length=settings.max_summary_length,
        enabled=settings.enabled
    )
    
    config = await ai_service.get_ai_config(db)
    return {
        "success": True,
        "message": "AI 设置已保存",
        "config": config
    }


@router.post("/ai/validate")
async def validate_ai_key(db: AsyncSession = Depends(get_db)):
    """
    验证 AI API Key 是否有效
    
    Returns:
        验证结果
    """
    is_valid, message = await ai_service.validate_api_key(db)
    return {
        "valid": is_valid,
        "message": message
    }


@router.post("/test/ai")
async def test_ai_summary(db: AsyncSession = Depends(get_db)):
    """
    测试 AI 摘要功能
    
    Returns:
        测试结果
    """
    success, result = await ai_service.generate_test_summary(db)
    
    if success:
        return {
            "success": True,
            "summary": result
        }
    else:
        return {
            "success": False,
            "message": result
        }

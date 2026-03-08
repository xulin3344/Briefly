from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Article, KeywordConfig, RSSSource, get_db
from app.services import (
    ai_service,
    cleanup_service,
    keyword_service,
    rss_service,
    scheduler,
    webhook_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Basic health check with a real database round-trip."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Health check database probe failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "Briefly",
                "version": "1.0.0",
                "database": "disconnected",
            },
        ) from exc

    return {
        "status": "healthy",
        "service": "Briefly",
        "version": "1.0.0",
        "database": "connected",
    }


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    """Return system status and aggregated counts."""
    from app.models import WebhookConfig

    sources_result = await db.execute(
        select(
            func.count(RSSSource.id).label("total_sources"),
            func.sum(case((RSSSource.enabled == True, 1), else_=0)).label(
                "enabled_sources"
            ),
        )
    )
    source_stats = sources_result.one()

    articles_result = await db.execute(
        select(
            func.count(Article.id).label("total_articles"),
            func.sum(case((Article.is_filtered == True, 1), else_=0)).label(
                "filtered_articles"
            ),
        )
    )
    article_stats = articles_result.one()

    keywords_result = await db.execute(
        select(
            func.count(KeywordConfig.id).label("total_keywords"),
            func.sum(case((KeywordConfig.enabled == True, 1), else_=0)).label(
                "enabled_keywords"
            ),
        )
    )
    keyword_stats = keywords_result.one()

    scheduler_status = scheduler.get_status()

    webhook_result = await db.execute(
        select(WebhookConfig).where(WebhookConfig.id == 1)
    )
    webhook_config = webhook_result.scalar_one_or_none()
    webhook_enabled = bool(
        webhook_config and webhook_config.enabled and webhook_config.url
    )

    ai_config = await ai_service.get_ai_config(db)

    return {
        "database": {
            "enabled_sources": source_stats.enabled_sources or 0,
            "total_sources": source_stats.total_sources or 0,
            "total_articles": article_stats.total_articles or 0,
            "filtered_articles": article_stats.filtered_articles or 0,
            "total_keywords": keyword_stats.total_keywords or 0,
            "enabled_keywords": keyword_stats.enabled_keywords or 0,
        },
        "scheduler": scheduler_status,
        "ai_configured": ai_config["has_api_key"],
        "webhook_enabled": webhook_enabled,
    }


class FetchRequest(BaseModel):
    background: bool = False


@router.post("/fetch")
async def trigger_fetch(
    background_tasks: BackgroundTasks,
    request: FetchRequest = FetchRequest(),
):
    if request.background:
        background_tasks.add_task(_run_fetch_task)
        return {
            "status": "started",
            "message": "RSS fetch task started in background",
        }

    return await scheduler.fetch_rss_task()


async def _run_fetch_task():
    try:
        await scheduler.fetch_rss_task()
    except Exception as exc:
        logger.error("Background RSS fetch task failed: %s", exc)


@router.post("/fetch/start")
async def start_fetch_background(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_fetch_task)
    return {
        "status": "started",
        "message": "RSS fetch task started in background",
    }


@router.post("/summarize")
async def trigger_summarize():
    return await scheduler.ai_summary_task()


@router.post("/run-pipeline")
async def run_full_pipeline():
    return await scheduler.run_full_pipeline()


@router.post("/test/rss")
async def test_rss_fetch(url: str):
    return await rss_service.test_rss_connection(url)


@router.post("/test/webhook")
async def test_webhook(db: AsyncSession = Depends(get_db)):
    return await webhook_service.test_webhook_connection_async(db)


@router.post("/scheduler/start")
def start_scheduler():
    if scheduler._is_running:
        return {
            "success": False,
            "message": "Scheduler is already running",
        }

    scheduler.start()
    return {
        "success": True,
        "message": "Scheduler started",
    }


@router.post("/scheduler/stop")
def stop_scheduler():
    if not scheduler._is_running:
        return {
            "success": False,
            "message": "Scheduler is not running",
        }

    scheduler.stop()
    return {
        "success": True,
        "message": "Scheduler stopped",
    }


class AISettingsUpdate(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    max_summary_length: Optional[int] = None
    enabled: Optional[bool] = None


@router.get("/ai/config")
async def get_ai_config(db: AsyncSession = Depends(get_db)):
    return await ai_service.get_ai_config(db)


@router.post("/ai/settings")
async def save_ai_settings(
    settings: AISettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    await ai_service.save_ai_settings(
        db,
        api_key=settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
        max_summary_length=settings.max_summary_length,
        enabled=settings.enabled,
    )

    config = await ai_service.get_ai_config(db)
    return {
        "success": True,
        "message": "AI settings saved",
        "config": config,
    }


@router.post("/ai/validate")
async def validate_ai_key(db: AsyncSession = Depends(get_db)):
    is_valid, message = await ai_service.validate_api_key(db)
    return {
        "valid": is_valid,
        "message": message,
    }


@router.post("/test/ai")
async def test_ai_summary(db: AsyncSession = Depends(get_db)):
    success, result = await ai_service.generate_test_summary(db)
    if success:
        return {
            "success": True,
            "summary": result,
        }

    return {
        "success": False,
        "message": result,
    }


@router.get("/articles/stats")
async def get_article_stats(db: AsyncSession = Depends(get_db)):
    return await cleanup_service.get_article_stats(db)


@router.post("/articles/cleanup")
async def cleanup_articles(
    days: int = None,
    db: AsyncSession = Depends(get_db),
):
    return await cleanup_service.cleanup_old_articles(db, days)

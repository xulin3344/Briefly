"""
文章清理服务

自动清理过期的文章，保持数据库精简
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy import func

from app.models import Article
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def cleanup_old_articles(db: AsyncSession, days: int = None) -> dict:
    """
    清理旧文章
    
    Args:
        db: 数据库会话
        days: 保留最近几天的文章，默认使用配置
        
    Returns:
        清理结果统计
    """
    cleanup_days = days if days is not None else settings.CLEANUP_DAYS
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=cleanup_days)
    
    try:
        # 先统计要删除的文章数量
        count_result = await db.execute(
            select(func.count(Article.id)).where(Article.published_at < cutoff_date)
        )
        old_count = count_result.scalar() or 0
        
        if old_count == 0:
            logger.info("没有需要清理的旧文章")
            return {
                "status": "success",
                "deleted_count": 0,
                "message": "没有需要清理的旧文章"
            }
        
        # 删除旧文章
        result = await db.execute(
            delete(Article).where(Article.published_at < cutoff_date)
        )
        await db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"成功清理 {deleted_count} 篇旧文章（{cleanup_days} 天前）")
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"成功清理 {deleted_count} 篇旧文章"
        }
        
    except Exception as e:
        logger.error(f"清理旧文章失败: {str(e)}")
        await db.rollback()
        return {
            "status": "error",
            "deleted_count": 0,
            "message": f"清理失败: {str(e)}"
        }


async def get_article_stats(db: AsyncSession) -> dict:
    """
    获取文章统计信息
    
    Args:
        db: 数据库会话
        
    Returns:
        文章统计信息
    """
    try:
        # 总文章数
        total_result = await db.execute(select(func.count(Article.id)))
        total_count = total_result.scalar() or 0
        
        # 最近3天的文章数
        three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
        recent_result = await db.execute(
            select(func.count(Article.id)).where(Article.published_at >= three_days_ago)
        )
        recent_count = recent_result.scalar() or 0
        
        # 最近7天的文章数
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        week_result = await db.execute(
            select(func.count(Article.id)).where(Article.published_at >= seven_days_ago)
        )
        week_count = week_result.scalar() or 0
        
        # 旧文章数（超过清理天数）
        cleanup_date = datetime.now(timezone.utc) - timedelta(days=settings.CLEANUP_DAYS)
        old_result = await db.execute(
            select(func.count(Article.id)).where(Article.published_at < cleanup_date)
        )
        old_count = old_result.scalar() or 0
        
        return {
            "total_articles": total_count,
            "recent_3_days": recent_count,
            "recent_7_days": week_count,
            "old_articles": old_count,
            "cleanup_days": settings.CLEANUP_DAYS
        }
        
    except Exception as e:
        logger.error(f"获取文章统计失败: {str(e)}")
        return {
            "total_articles": 0,
            "recent_3_days": 0,
            "recent_7_days": 0,
            "old_articles": 0,
            "cleanup_days": settings.CLEANUP_DAYS,
            "error": str(e)
        }

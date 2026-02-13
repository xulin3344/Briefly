from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
import logging

from app.models import WebhookConfig, Article
from app.services.webhook_service import send_webhook_message, build_favorites_webhook_message
from app.config import settings

logger = logging.getLogger(__name__)

# 全局调度器
scheduler = AsyncIOScheduler()


def get_sync_db():
    """获取同步数据库会话"""
    engine = create_engine(settings.DATABASE_URL.replace("+aiosqlite", ""))
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def webhook_push_task():
    """定时推送文章任务"""
    db = get_sync_db()
    
    try:
        # 获取配置
        result = db.execute(select(WebhookConfig).where(WebhookConfig.id == 1))
        config = result.scalar_one_or_none()
        
        if not config or not config.schedule_enabled:
            logger.info("定时推送已关闭或未配置")
            return
        
        if not config.enabled or not config.url:
            logger.warning("Webhook 未启用，跳过定时推送")
            return
        
        pushed = 0
        
        # 推送收藏文章
        if config.push_favorites:
            result = db.execute(
                select(Article).where(Article.is_favorite == True).order_by(Article.published_at.desc())
            )
            favorites = result.scalars().all()
            
            if favorites:
                articles = [{"title": a.title, "link": a.link} for a in favorites]
                message = build_favorites_webhook_message(articles, config.platform)
                success = send_webhook_message(config.url, message)
                if success:
                    pushed += len(favorites)
                    logger.info(f"定时推送 {len(favorites)} 篇收藏文章")
        
        # 推送过滤文章
        if config.push_filtered:
            result = db.execute(
                select(Article).where(Article.is_filtered == True).order_by(Article.published_at.desc())
            )
            filtered = result.scalars().all()
            
            if filtered:
                articles = [{"title": a.title, "link": a.link} for a in filtered]
                message = build_favorites_webhook_message(articles, config.platform)
                success = send_webhook_message(config.url, message)
                if success:
                    pushed += len(filtered)
                    logger.info(f"定时推送 {len(filtered)} 篇过滤文章")
        
        if pushed > 0:
            logger.info(f"定时推送完成，共推送 {pushed} 篇文章")
        else:
            logger.info("定时推送：无文章可推送")
            
    except Exception as e:
        logger.error(f"定时推送任务失败: {str(e)}")
    finally:
        db.close()


def update_webhook_schedule():
    """更新 Webhook 定时推送任务"""
    # 移除现有任务
    for job in scheduler.get_jobs():
        if job.id == "webhook_push":
            job.remove()
    
    db = get_sync_db()
    
    try:
        result = db.execute(select(WebhookConfig).where(WebhookConfig.id == 1))
        config = result.scalar_one_or_none()
        
        if not config or not config.schedule_enabled:
            logger.info("定时推送已关闭")
            return
        
        # 解析时间
        time_parts = config.schedule_time.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        # 根据频率设置触发器
        if config.schedule_frequency == "hourly":
            trigger = IntervalTrigger(hours=1)
            logger.info("设置每小时定时推送")
        elif config.schedule_frequency == "daily":
            trigger = CronTrigger(hour=hour, minute=minute)
            logger.info(f"设置每日定时推送: {config.schedule_time}")
        elif config.schedule_frequency == "weekly":
            day_of_week = config.schedule_day_of_week - 1  # Cron: 0=周一
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
            logger.info(f"设置每周定时推送: 周{config.schedule_day_of_week} {config.schedule_time}")
        elif config.schedule_frequency == "monthly":
            trigger = CronTrigger(day=config.schedule_day_of_month, hour=hour, minute=minute)
            logger.info(f"设置每月定时推送: 每月{config.schedule_day_of_month}日 {config.schedule_time}")
        else:
            logger.warning(f"未知推送频率: {config.schedule_frequency}")
            return
        
        scheduler.add_job(webhook_push_task, trigger, id="webhook_push", replace_existing=True)
        logger.info("Webhook 定时推送任务已更新")
        
    except Exception as e:
        logger.error(f"更新定时推送任务失败: {str(e)}")
    finally:
        db.close()


def start_webhook_scheduler():
    """启动 Webhook 调度器"""
    try:
        # 尝试添加现有任务
        update_webhook_schedule()
        
        if not scheduler.running:
            scheduler.start()
            logger.info("Webhook 定时调度器已启动")
    except Exception as e:
        logger.error(f"启动 Webhook 调度器失败: {str(e)}")


def stop_webhook_scheduler():
    """停止 Webhook 调度器"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Webhook 定时调度器已停止")
    except Exception as e:
        logger.error(f"停止 Webhook 调度器失败: {str(e)}")

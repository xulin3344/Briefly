from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from sqlalchemy import delete

from app.config import settings
from app.models import AsyncSessionLocal, Article, RSSSource
from app.services import rss_service, keyword_service, ai_service, cleanup_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    def start(self):
        if self._is_running:
            logger.warning("调度器已在运行中")
            return
        
        # RSS 抓取任务 - 每小时执行
        self.scheduler.add_job(
            self.fetch_rss_task,
            trigger=IntervalTrigger(minutes=settings.FETCH_INTERVAL_MINUTES),
            id='fetch_rss',
            name='RSS Feed Fetcher',
            replace_existing=True,
            max_instances=1
        )
        
        # AI 总结任务 - 每小时的第5和第35分钟执行
        self.scheduler.add_job(
            self.ai_summary_task,
            trigger=CronTrigger(minute='5,35'),
            id='ai_summary',
            name='AI Article Summarizer',
            replace_existing=True,
            max_instances=2
        )
        
        # 每日重置任务 - 每天指定时间执行
        if settings.AUTO_RESET_ENABLED:
            self.scheduler.add_job(
                self.daily_reset_task,
                trigger=CronTrigger(hour=settings.AUTO_RESET_HOUR, minute=0),
                id='daily_reset',
                name='Daily Database Reset',
                replace_existing=True,
                max_instances=1
            )
            logger.info(f"每日重置任务已启用，重置时间: 每天 {settings.AUTO_RESET_HOUR}:00")
        
        # 文章清理任务 - 每天凌晨2点执行
        if settings.AUTO_CLEANUP_ENABLED:
            self.scheduler.add_job(
                self.cleanup_task,
                trigger=CronTrigger(hour=2, minute=0),
                id='cleanup_articles',
                name='Old Articles Cleanup',
                replace_existing=True,
                max_instances=1
            )
            logger.info(f"文章自动清理任务已启用，清理 {settings.CLEANUP_DAYS} 天前的文章")
        
        self.scheduler.start()
        self._is_running = True
        
        logger.info(
            f"定时任务调度器已启动，"
            f"抓取间隔: {settings.FETCH_INTERVAL_MINUTES} 分钟"
        )
    
    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("定时任务调度器已停止")
    
    def run_now(self, task_id: str):
        if task_id == 'fetch_rss':
            return self.fetch_rss_task()
        elif task_id == 'ai_summary':
            return self.ai_summary_task()
        elif task_id == 'daily_reset':
            return self.daily_reset_task()
        elif task_id == 'cleanup_articles':
            return self.cleanup_task()
        else:
            logger.error(f"未知任务 ID: {task_id}")
            return None
    
    async def fetch_rss_task(self):
        logger.info("=" * 50)
        logger.info(f"[{datetime.now()}] 开始执行 RSS 抓取任务")
        
        async with AsyncSessionLocal() as db:
            try:
                results = await rss_service.fetch_and_save_all_sources(db)
                
                total_articles = sum(v for v in results.values() if v > 0)
                failed_sources = sum(1 for v in results.values() if v < 0)
                
                logger.info(f"RSS 抓取完成: 新增 {total_articles} 篇文章, "
                           f"失败 {failed_sources} 个源")
                
                # 抓取完成后自动运行过滤
                filtered_count = await keyword_service.filter_articles_by_keywords(db)
                logger.info(f"关键词过滤完成: 过滤 {len(filtered_count)} 篇文章")
                
                return {
                    "status": "success",
                    "new_articles": total_articles,
                    "filtered_count": len(filtered_count),
                    "failed_sources": failed_sources
                }
                
            except Exception as e:
                logger.error(f"RSS 抓取任务异常: {str(e)}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    async def ai_summary_task(self):
        logger.info("=" * 50)
        logger.info(f"[{datetime.now()}] 开始执行 AI 总结任务")
        
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    select(Article).where(
                        Article.has_summary == False,
                        Article.is_filtered == False,
                        Article.content.isnot(None),
                        Article.content != ''
                    ).limit(20)
                )
                articles = result.scalars().all()
                
                if not articles:
                    logger.info("没有需要生成摘要的文章")
                    return {
                        "status": "success",
                        "message": "没有待处理文章"
                    }
                
                logger.info(f"找到 {len(articles)} 篇待生成摘要的文章")
                
                success_count = await ai_service.summarize_articles_batch(
                    articles, db, max_concurrent=5
                )
                
                logger.info(f"AI 总结完成: 成功 {success_count}/{len(articles)} 篇")
                
                return {
                    "status": "success",
                    "total": len(articles),
                    "success": success_count
                }
                
            except Exception as e:
                logger.error(f"AI 总结任务异常: {str(e)}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    async def daily_reset_task(self):
        """
        每日重置任务
        清空所有文章数据，但保留 RSS 源和关键词配置
        """
        logger.info("=" * 50)
        logger.info(f"[{datetime.now()}] 开始执行每日重置任务")
        
        if not settings.AUTO_RESET_ENABLED:
            logger.info("自动重置已禁用，跳过")
            return {
                "status": "skipped",
                "message": "自动重置已禁用"
            }
        
        async with AsyncSessionLocal() as db:
            try:
                # 删除所有文章
                await db.execute(delete(Article))
                await db.commit()
                
                logger.info("文章数据已清空")
                
                # 重置 RSS 源的抓取统计
                from sqlalchemy import update
                await db.execute(
                    update(RSSSource).values(
                        fetch_error_count=0,
                        last_fetched=None
                    )
                )
                await db.commit()
                
                logger.info("RSS 源抓取统计已重置")
                
                return {
                    "status": "success",
                    "message": "每日重置完成"
                }
                
            except Exception as e:
                logger.error(f"每日重置任务异常: {str(e)}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    async def cleanup_task(self):
        """
        文章清理任务
        自动清理过期的旧文章
        """
        logger.info("=" * 50)
        logger.info(f"[{datetime.now()}] 开始执行文章清理任务")
        
        if not settings.AUTO_CLEANUP_ENABLED:
            logger.info("自动清理已禁用，跳过")
            return {
                "status": "skipped",
                "message": "自动清理已禁用"
            }
        
        async with AsyncSessionLocal() as db:
            try:
                result = await cleanup_service.cleanup_old_articles(db)
                
                if result["status"] == "success":
                    logger.info(f"文章清理完成: 删除 {result['deleted_count']} 篇旧文章")
                else:
                    logger.error(f"文章清理失败: {result['message']}")
                
                return result
                
            except Exception as e:
                logger.error(f"文章清理任务异常: {str(e)}")
                return {
                    "status": "error",
                    "message": str(e)
                }
    
    def get_status(self) -> dict:
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "running": self._is_running,
            "jobs": jobs
        }
    
    async def run_full_pipeline(self):
        logger.info("=" * 50)
        logger.info("开始执行完整处理流程")
        
        fetch_result = await self.fetch_rss_task()
        summary_result = await self.ai_summary_task()
        
        return {
            "fetch": fetch_result,
            "summary": summary_result
        }


scheduler = TaskScheduler()


def get_scheduler() -> TaskScheduler:
    return scheduler


async def start_scheduler():
    scheduler.start()
    logger.info("调度器已启动（异步）")


def sync_start_scheduler():
    scheduler.start()
    logger.info("调度器已启动（同步）")

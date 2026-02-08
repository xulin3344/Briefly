from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from app.config import settings
from app.models import AsyncSessionLocal, Article
from app.services import rss_service, keyword_service, ai_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskScheduler:
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False
    
    def start(self):
        if self._is_running:
            logger.warning("调度器已在运行中")
            return
        
        self.scheduler.add_job(
            self.fetch_rss_task,
            trigger=IntervalTrigger(minutes=settings.FETCH_INTERVAL_MINUTES),
            id='fetch_rss',
            name='RSS Feed Fetcher',
            replace_existing=True,
            max_instances=1
        )
        
        self.scheduler.add_job(
            self.ai_summary_task,
            trigger=CronTrigger(minute='5,35'),
            id='ai_summary',
            name='AI Article Summarizer',
            replace_existing=True,
            max_instances=2
        )
        
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

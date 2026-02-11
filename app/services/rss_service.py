import asyncio
import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.config import settings
from app.models import Article, RSSSource
from app.core.logging import get_logger

logger = get_logger(__name__)


class RSSFetchError(Exception):
    """RSS 抓取异常基类"""
    pass


class RSSParseError(RSSFetchError):
    """RSS 解析错误"""
    pass


class RSSNetworkError(RSSFetchError):
    """网络连接错误（可重试）"""
    pass


class RSSTimeoutError(RSSFetchError):
    """请求超时错误（可重试）"""
    pass


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    
    date_formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d",
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    logger.warning(f"无法解析日期字符串: {date_str}")
    return None


def extract_entry_data(entry) -> Dict:
    guid = getattr(entry, 'id', None) or getattr(entry, 'link', '')
    
    published = getattr(entry, 'published', None) or \
                getattr(entry, 'updated', None) or \
                getattr(entry, 'created', None)
    published_at = parse_date(published)
    
    if not published_at:
        published_at = datetime.now(timezone.utc)
    
    content = ""
    if hasattr(entry, 'content') and entry.content:
        content = entry.content[0].value if entry.content else ""
    elif hasattr(entry, 'summary'):
        content = entry.summary
    
    if content:
        import re
        content = re.sub(r'<[^>]+>', '', content)
        content = content.strip()
    
    description = getattr(entry, 'summary', None) or ""
    if not description and content:
        description = content[:500]
    
    author = getattr(entry, 'author', None) or \
             getattr(entry, 'authors', [{}])[0].get('name', None) if hasattr(entry, 'authors') else None
    
    title = getattr(entry, 'title', '无标题')
    if not title:
        title = "无标题"
    
    def fix_encoding(text):
        if not text:
            return text
        try:
            return text.encode('latin1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            try:
                return text.encode('latin1').decode('gbk')
            except (UnicodeDecodeError, UnicodeEncodeError):
                return text
    
    title = fix_encoding(title)
    description = fix_encoding(description)
    content = fix_encoding(content)
    if author:
        author = fix_encoding(author)
    
    return {
        "guid": guid,
        "title": title,
        "link": getattr(entry, 'link', ''),
        "description": description,
        "content": content,
        "author": author,
        "published_at": published_at
    }


# 定义可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    RSSTimeoutError,
    RSSNetworkError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, log_level=20),  # INFO level
    reraise=True,
)
async def fetch_rss_feed(source: RSSSource) -> List[Dict]:
    """
    异步抓取单个 RSS 源
    使用 httpx.AsyncClient 避免阻塞事件循环
    使用 tenacity 实现自动重试机制
    
    重试策略：
    - 最多重试 3 次
    - 指数退避：2s, 4s, 8s（最大 10s）
    - 仅对网络错误和超时重试，解析错误不重试
    """
    logger.info(f"开始抓取 RSS 源: {source.name} ({source.url})")
    
    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.get(source.url, follow_redirects=True)
            response.raise_for_status()
            response_text = response.text
    except httpx.TimeoutException as e:
        logger.warning(f"RSS 源请求超时: {source.name}, 将重试...")
        raise RSSTimeoutError(f"请求超时: {source.url}")
    except httpx.ConnectError as e:
        logger.warning(f"RSS 源连接失败: {source.name}, 将重试...")
        raise RSSNetworkError(f"连接失败: {source.url}, 错误: {str(e)}")
    except httpx.HTTPStatusError as e:
        # HTTP 错误（如 404, 500）不重试
        raise RSSNetworkError(f"HTTP 错误: {e.response.status_code} {source.url}")
    
    try:
        # feedparser 是同步库，但在 I/O 完成后解析是 CPU 密集型操作
        # 对于大量数据，可以考虑在线程池中运行
        feed = feedparser.parse(response_text)
        
        if feed.bozo:
            # 解析错误不重试
            raise RSSParseError(f"RSS 解析失败: {source.url}")
        
        if not hasattr(feed, 'entries') or not feed.entries:
            logger.info(f"RSS 源没有新条目: {source.name}")
            return []
        
        articles = []
        for entry in feed.entries:
            entry_data = extract_entry_data(entry)
            articles.append(entry_data)
        
        logger.info(f"成功抓取 {len(articles)} 篇文章: {source.name}")
        return articles
        
    except RSSParseError:
        raise
    except Exception as e:
        raise RSSParseError(f"解析 RSS 失败: {source.url}, 错误: {str(e)}")


async def is_duplicate_article(db: AsyncSession, source_id: int, guid: str) -> bool:
    result = await db.execute(
        select(Article).where(
            Article.source_id == source_id,
            Article.guid == guid
        )
    )
    existing = result.scalar_one_or_none()
    return existing is not None


async def save_articles(db: AsyncSession, source_id: int, articles: List[Dict]) -> int:
    saved_count = 0
    
    for article_data in articles:
        if await is_duplicate_article(db, source_id, article_data['guid']):
            logger.debug(f"文章已存在，跳过: {article_data['title'][:50]}...")
            continue
        
        article = Article(
            source_id=source_id,
            guid=article_data['guid'],
            title=article_data['title'],
            link=article_data['link'],
            description=article_data.get('description', ''),
            content=article_data.get('content', ''),
            author=article_data.get('author'),
            published_at=article_data.get('published_at'),
            is_filtered=False,
            has_summary=False
        )
        
        db.add(article)
        saved_count += 1
    
    await db.commit()
    logger.info(f"成功保存 {saved_count} 篇新文章")
    return saved_count


async def fetch_and_save_all_sources(db: AsyncSession) -> Dict[int, int]:
    """
    并发抓取所有启用的 RSS 源
    使用 asyncio.gather 实现并发请求，提高抓取效率
    
    特性：
    - 单个源抓取失败不会影响其他源
    - 每个源都有独立的重试机制
    - 返回每个源的抓取结果
    """
    result = await db.execute(select(RSSSource).where(RSSSource.enabled == True))
    sources = result.scalars().all()
    
    if not sources:
        logger.info("没有启用的 RSS 源")
        return {}
    
    results = {}
    
    async def fetch_single_source(source: RSSSource) -> tuple[int, List[Dict] | Exception]:
        """
        抓取单个源并返回结果
        异常会被捕获并返回，确保不会中断 asyncio.gather
        """
        try:
            articles = await fetch_rss_feed(source)
            return source.id, articles
        except RSSFetchError as e:
            # RSS 相关错误（已重试后仍失败）
            logger.error(f"RSS 抓取失败 [{source.name}]: {str(e)}")
            return source.id, e
        except Exception as e:
            # 其他未知错误
            logger.exception(f"RSS 抓取未知错误 [{source.name}]: {str(e)}")
            return source.id, e
    
    # 使用 asyncio.gather 并发执行所有抓取任务
    # return_exceptions=False 因为我们已经在 fetch_single_source 中处理了异常
    fetch_tasks = [fetch_single_source(source) for source in sources]
    fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=False)
    
    # 处理抓取结果
    for source_id, fetch_result in fetch_results:
        source = next(s for s in sources if s.id == source_id)
        
        if isinstance(fetch_result, Exception):
            logger.error(f"抓取 RSS 源失败: {source.name}, 错误: {str(fetch_result)}")
            source.fetch_error_count += 1
            await db.commit()
            results[source_id] = -1
        else:
            articles = fetch_result
            if articles:
                saved = await save_articles(db, source_id, articles)
                results[source_id] = saved
            else:
                results[source_id] = 0
            
            source.last_fetched = datetime.utcnow()
            source.fetch_error_count = 0
            await db.commit()
    
    # 汇总日志
    success_count = sum(1 for v in results.values() if v >= 0)
    failed_count = sum(1 for v in results.values() if v < 0)
    total_articles = sum(v for v in results.values() if v > 0)
    
    logger.info(
        f"RSS 抓取完成: 成功 {success_count}/{len(sources)} 个源, "
        f"失败 {failed_count} 个源, 共 {total_articles} 篇新文章"
    )
    
    return results


async def test_rss_connection(url: str) -> Dict:
    """
    异步测试 RSS 源连接
    """
    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            response_text = response.text
        
        feed = feedparser.parse(response_text)
        
        if feed.bozo:
            return {
                "success": False,
                "message": "RSS 解析失败，可能不是有效的 RSS 源",
                "entry_count": 0
            }
        
        title = feed.feed.get('title', 'Unknown') if hasattr(feed, 'feed') else 'Unknown'
        
        return {
            "success": True,
            "message": "RSS 源连接正常",
            "title": title,
            "entry_count": len(feed.entries) if hasattr(feed, 'entries') else 0
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}",
            "entry_count": 0
        }

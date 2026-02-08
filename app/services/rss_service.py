import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Optional
import httpx
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models import Article, RSSSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RSSFetchError(Exception):
    pass


class RSSParseError(RSSFetchError):
    pass


class RSSNetworkError(RSSFetchError):
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


def fetch_rss_feed(source: RSSSource) -> List[Dict]:
    logger.info(f"开始抓取 RSS 源: {source.name} ({source.url})")
    
    try:
        with httpx.Client(timeout=settings.REQUEST_TIMEOUT) as client:
            response = client.get(source.url, follow_redirects=True)
            response.raise_for_status()
    except httpx.TimeoutException:
        raise RSSNetworkError(f"请求超时: {source.url}")
    except httpx.ConnectError as e:
        raise RSSNetworkError(f"连接失败: {source.url}, 错误: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise RSSNetworkError(f"HTTP 错误: {e.response.status_code} {source.url}")
    
    try:
        feed = feedparser.parse(response.text)
        
        if feed.bozo:
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
    result = await db.execute(select(RSSSource).where(RSSSource.enabled == True))
    sources = result.scalars().all()
    
    results = {}
    
    for source in sources:
        try:
            articles = fetch_rss_feed(source)
            
            if articles:
                saved = await save_articles(db, source.id, articles)
                results[source.id] = saved
            else:
                results[source.id] = 0
            
            source.last_fetched = datetime.utcnow()
            source.fetch_error_count = 0
            await db.commit()
            
        except RSSFetchError as e:
            logger.error(f"抓取 RSS 源失败: {source.name}, 错误: {str(e)}")
            source.fetch_error_count += 1
            await db.commit()
            results[source.id] = -1
    
    return results


def test_rss_connection(url: str) -> Dict:
    try:
        with httpx.Client(timeout=settings.REQUEST_TIMEOUT) as client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
        
        feed = feedparser.parse(response.text)
        
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

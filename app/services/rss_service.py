import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.logging import get_logger
from app.models import Article, RSSSource

logger = get_logger(__name__)


class RSSFetchError(Exception):
    """Base exception for RSS fetch failures."""


class RSSParseError(RSSFetchError):
    """Raised when a feed payload cannot be parsed."""


class RSSNetworkError(RSSFetchError):
    """Raised when a network request fails."""


class RSSTimeoutError(RSSFetchError):
    """Raised when a network request times out."""


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
            parsed = datetime.strptime(date_str, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue

    logger.warning("Failed to parse published date: %s", date_str)
    return None


def _fix_encoding(text: Optional[str]) -> Optional[str]:
    if not text:
        return text

    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        try:
            return text.encode("latin1").decode("gbk")
        except (UnicodeDecodeError, UnicodeEncodeError):
            return text


def extract_entry_data(entry: Any) -> Optional[Dict[str, Any]]:
    guid = getattr(entry, "id", None) or getattr(entry, "link", "")
    published = (
        getattr(entry, "published", None)
        or getattr(entry, "updated", None)
        or getattr(entry, "created", None)
    )
    published_at = parse_date(published)

    if settings.FETCH_TODAY_ONLY and published_at:
        today_start = datetime.now(timezone.utc).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        if published_at < today_start:
            return None

    if not published_at:
        published_at = datetime.now(timezone.utc)

    content = ""
    if hasattr(entry, "content") and entry.content:
        content = entry.content[0].value if entry.content else ""
    elif hasattr(entry, "summary"):
        content = entry.summary

    if content:
        content = re.sub(r"<[^>]+>", "", content).strip()

    description = getattr(entry, "summary", None) or ""
    if not description and content:
        description = content[: settings.DESCRIPTION_MAX_LENGTH]

    author = getattr(entry, "author", None)
    if not author and hasattr(entry, "authors") and entry.authors:
        author = entry.authors[0].get("name")

    title = getattr(entry, "title", "") or "Untitled"

    return {
        "guid": guid,
        "title": _fix_encoding(title) or "Untitled",
        "link": getattr(entry, "link", ""),
        "description": _fix_encoding(description) or "",
        "content": _fix_encoding(content) or "",
        "author": _fix_encoding(author),
        "published_at": published_at,
    }


RETRYABLE_EXCEPTIONS = (
    RSSTimeoutError,
    RSSNetworkError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
)


@retry(
    stop=stop_after_attempt(settings.MAX_RETRY_ATTEMPTS),
    wait=wait_exponential(
        multiplier=1,
        min=settings.RETRY_MIN_WAIT,
        max=settings.RETRY_MAX_WAIT,
    ),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, log_level=20),
    reraise=True,
)
async def fetch_rss_feed(source: RSSSource) -> list[Dict[str, Any]]:
    logger.info("Fetching RSS source: %s (%s)", source.name, source.url)

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.get(source.url, follow_redirects=True)
            response.raise_for_status()
            response_text = response.text
    except httpx.TimeoutException as exc:
        logger.warning("RSS request timed out for %s", source.name)
        raise RSSTimeoutError(f"Request timed out: {source.url}") from exc
    except httpx.ConnectError as exc:
        logger.warning("RSS connection failed for %s", source.name)
        raise RSSNetworkError(f"Connection failed: {source.url}") from exc
    except httpx.HTTPStatusError as exc:
        raise RSSNetworkError(
            f"HTTP error: {exc.response.status_code} {source.url}"
        ) from exc

    try:
        feed = feedparser.parse(response_text)
        if feed.bozo:
            raise RSSParseError(f"RSS parse failed: {source.url}")

        if not getattr(feed, "entries", None):
            logger.info("RSS source has no new entries: %s", source.name)
            return []

        articles: list[Dict[str, Any]] = []
        skipped_count = 0
        for entry in feed.entries:
            entry_data = extract_entry_data(entry)
            if entry_data is None:
                skipped_count += 1
                continue
            articles.append(entry_data)

        if skipped_count:
            logger.info("Skipped %s non-today articles for %s", skipped_count, source.name)

        logger.info("Fetched %s articles from %s", len(articles), source.name)
        return articles
    except RSSParseError:
        raise
    except Exception as exc:
        raise RSSParseError(f"Failed to parse RSS feed: {source.url}") from exc


async def is_duplicate_article(db: AsyncSession, source_id: int, guid: str) -> bool:
    result = await db.execute(
        select(Article).where(
            Article.source_id == source_id,
            Article.guid == guid,
        )
    )
    return result.scalar_one_or_none() is not None


async def save_articles(
    db: AsyncSession,
    source_id: int,
    articles: list[Dict[str, Any]],
) -> int:
    if not articles:
        return 0

    guids = {article["guid"] for article in articles if article.get("guid")}
    existing_guids: set[str] = set()

    if guids:
        result = await db.execute(
            select(Article.guid).where(
                Article.source_id == source_id,
                Article.guid.in_(guids),
            )
        )
        existing_guids = set(result.scalars().all())

    saved_count = 0
    for article_data in articles:
        guid = article_data.get("guid")
        if guid and guid in existing_guids:
            logger.debug("Skipping duplicate article: %s", article_data["title"][:50])
            continue

        article = Article(
            source_id=source_id,
            guid=article_data["guid"],
            title=article_data["title"],
            link=article_data["link"],
            description=article_data.get("description", ""),
            content=article_data.get("content", ""),
            author=article_data.get("author"),
            published_at=article_data.get("published_at"),
            is_filtered=False,
            has_summary=False,
        )
        db.add(article)
        if guid:
            existing_guids.add(guid)
        saved_count += 1

    await db.commit()
    logger.info("Saved %s new articles", saved_count)
    return saved_count


async def fetch_and_save_all_sources(db: AsyncSession) -> Dict[int, int]:
    result = await db.execute(select(RSSSource).where(RSSSource.enabled == True))
    sources = result.scalars().all()

    if not sources:
        logger.info("No enabled RSS sources found")
        return {}

    results: Dict[int, int] = {}
    source_map = {source.id: source for source in sources}

    async def fetch_single_source(
        source: RSSSource,
    ) -> tuple[int, list[Dict[str, Any]] | Exception]:
        try:
            articles = await fetch_rss_feed(source)
            return source.id, articles
        except RSSFetchError as exc:
            logger.error("RSS fetch failed [%s]: %s", source.name, exc)
            return source.id, exc
        except Exception as exc:
            logger.exception("Unexpected RSS fetch error [%s]: %s", source.name, exc)
            return source.id, exc

    fetch_results = await asyncio.gather(
        *(fetch_single_source(source) for source in sources),
        return_exceptions=False,
    )

    for source_id, fetch_result in fetch_results:
        source = source_map[source_id]
        if isinstance(fetch_result, Exception):
            source.fetch_error_count += 1
            await db.commit()
            results[source_id] = -1
            continue

        saved = await save_articles(db, source_id, fetch_result)
        source.last_fetched = datetime.utcnow()
        source.fetch_error_count = 0
        await db.commit()
        results[source_id] = saved

    success_count = sum(1 for value in results.values() if value >= 0)
    failed_count = sum(1 for value in results.values() if value < 0)
    total_articles = sum(value for value in results.values() if value > 0)
    logger.info(
        "RSS fetch complete: success %s/%s, failed %s, new articles %s",
        success_count,
        len(sources),
        failed_count,
        total_articles,
    )
    return results


async def test_rss_connection(url: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            response_text = response.text

        feed = feedparser.parse(response_text)
        if feed.bozo:
            return {
                "success": False,
                "message": "RSS parsing failed. The URL may not be a valid feed.",
                "entry_count": 0,
            }

        title = feed.feed.get("title", "Unknown") if hasattr(feed, "feed") else "Unknown"
        return {
            "success": True,
            "message": "RSS connection succeeded.",
            "title": title,
            "entry_count": len(feed.entries) if hasattr(feed, "entries") else 0,
        }
    except Exception as exc:
        return {
            "success": False,
            "message": f"Connection failed: {exc}",
            "entry_count": 0,
        }

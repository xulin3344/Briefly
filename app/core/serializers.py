"""Shared serialization utilities for the application."""
from datetime import datetime
from typing import Optional


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime to ISO format string."""
    return dt.isoformat() if dt else None


def serialize_rss_source(source) -> dict:
    """Serialize RSS source to dictionary."""
    return {
        "id": source.id,
        "name": source.name,
        "url": source.url,
        "description": source.description,
        "enabled": source.enabled,
        "last_fetched": format_datetime(source.last_fetched),
        "fetch_error_count": source.fetch_error_count,
        "created_at": format_datetime(source.created_at)
    }


def serialize_article(article) -> dict:
    """Serialize article to dictionary."""
    content_preview = None
    if article.content:
        content_preview = article.content[:200] + "..." if len(article.content) > 200 else article.content
    
    return {
        "id": article.id,
        "source_id": article.source_id,
        "guid": article.guid,
        "title": article.title,
        "link": article.link,
        "description": article.description,
        "content_preview": content_preview,
        "author": article.author,
        "published_at": format_datetime(article.published_at),
        "is_filtered": article.is_filtered,
        "has_summary": article.has_summary,
        "summary": article.summary,
        "is_read": article.is_read,
        "is_favorite": article.is_favorite,
        "fetched_at": format_datetime(article.fetched_at),
        "created_at": format_datetime(article.created_at)
    }


def serialize_keyword(keyword) -> dict:
    """Serialize keyword to dictionary."""
    return {
        "id": keyword.id,
        "keyword": keyword.keyword,
        "enabled": keyword.enabled,
        "match_count": keyword.match_count,
        "created_at": format_datetime(keyword.created_at),
        "updated_at": format_datetime(keyword.updated_at)
    }

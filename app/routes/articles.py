from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import logging
from datetime import datetime

from app.models import get_db, Article, RSSSource, KeywordConfig
from app.services import ai_service, webhook_service, keyword_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["文章管理"])


def article_to_dict(article: Article) -> dict:
    def fmt(dt):
        return dt.isoformat() if dt else None
    
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
        "published_at": fmt(article.published_at),
        "is_filtered": article.is_filtered,
        "has_summary": article.has_summary,
        "summary": article.summary,
        "is_read": article.is_read,
        "is_favorite": article.is_favorite,
        "fetched_at": fmt(article.fetched_at),
        "created_at": fmt(article.created_at)
    }


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    source_id: int
    guid: str
    title: str
    link: str
    description: Optional[str] = None
    content_preview: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    is_filtered: bool
    has_summary: bool
    summary: Optional[str] = None
    is_read: bool
    is_favorite: bool
    fetched_at: Optional[str] = None
    created_at: Optional[str] = None


class ArticleListResponse(BaseModel):
    articles: List[ArticleResponse]
    total: int
    page: int
    page_size: int


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    source_id: int = Query(None, description="RSS 源 ID 筛选"),
    filtered: bool = Query(None, description="是否被过滤"),
    has_summary: bool = Query(None, description="是否有摘要"),
    is_read: bool = Query(None, description="是否已读"),
    keyword: str = Query(None, description="标题关键词搜索"),
    db: AsyncSession = Depends(get_db)
):
    # 构建查询条件
    conditions = []
    if source_id is not None:
        conditions.append(Article.source_id == source_id)
    if filtered is not None:
        conditions.append(Article.is_filtered == filtered)
    if has_summary is not None:
        conditions.append(Article.has_summary == has_summary)
    if is_read is not None:
        conditions.append(Article.is_read == is_read)
    if keyword:
        conditions.append(Article.title.contains(keyword))
    
    where_clause = and_(*conditions) if conditions else None
    
    # 优化：使用 SQL COUNT 查询计算总数，避免加载所有数据到内存
    count_query = select(func.count(Article.id))
    if where_clause is not None:
        count_query = count_query.where(where_clause)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页查询 - 只获取需要的数据
    query = select(Article)
    if where_clause is not None:
        query = query.where(where_clause)
    query = query.order_by(Article.published_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    return {
        "articles": [ArticleResponse(**article_to_dict(a)) for a in articles],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/favorites", response_model=List[ArticleResponse])
async def get_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Article).where(Article.is_favorite == True)
    query = query.order_by(Article.published_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    return [ArticleResponse(**article_to_dict(a)) for a in articles]


@router.get("/filtered", response_model=List[ArticleResponse])
async def get_filtered_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Article).where(Article.is_filtered == True)
    query = query.order_by(Article.published_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    return [ArticleResponse(**article_to_dict(a)) for a in articles]


@router.get("/keywords", response_model=List[ArticleResponse])
async def get_keyword_matched_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(KeywordConfig).where(KeywordConfig.enabled == True)
    )
    keywords = result.scalars().all()
    
    if not keywords:
        return []
    
    keyword_list = [kw.keyword.lower() for kw in keywords]
    
    conditions = []
    for keyword in keyword_list:
        keyword_pattern = f'%{keyword}%'
        conditions.append(
            or_(
                Article.title.ilike(keyword_pattern),
                Article.description.ilike(keyword_pattern),
                Article.content.ilike(keyword_pattern)
            )
        )
    
    query = select(Article).where(or_(*conditions))
    query = query.order_by(Article.published_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    return [ArticleResponse(**article_to_dict(a)) for a in articles]


@router.get("/statistics")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    
    result = await db.execute(select(func.count(Article.id)))
    total = result.scalar() or 0
    
    result = await db.execute(select(func.count(Article.id)).where(Article.is_read == False))
    unread = result.scalar() or 0
    
    result = await db.execute(select(func.count(Article.id)).where(Article.is_filtered == True))
    filtered = result.scalar() or 0
    
    result = await db.execute(select(func.count(Article.id)).where(Article.has_summary == True))
    with_summary = result.scalar() or 0
    
    result = await db.execute(select(func.count(Article.id)).where(Article.is_favorite == True))
    favorites = result.scalar() or 0
    
    result = await db.execute(select(func.count(RSSSource.id)))
    sources_count = result.scalar() or 0
    
    result = await db.execute(select(func.count(RSSSource.id)).where(RSSSource.enabled == True))
    enabled_sources = result.scalar() or 0
    
    return {
        "total_articles": total,
        "unread_articles": unread,
        "filtered_articles": filtered,
        "articles_with_summary": with_summary,
        "favorite_articles": favorites,
        "total_sources": sources_count,
        "enabled_sources": enabled_sources
    }


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    return ArticleResponse(**article_to_dict(article))


@router.put("/{article_id}/read", response_model=ArticleResponse)
async def mark_as_read(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    article.is_read = True
    await db.commit()
    await db.refresh(article)
    
    return ArticleResponse(**article_to_dict(article))


@router.put("/{article_id}/favorite", response_model=ArticleResponse)
async def toggle_favorite(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    article.is_favorite = not article.is_favorite
    await db.commit()
    await db.refresh(article)
    
    return ArticleResponse(**article_to_dict(article))


@router.post("/{article_id}/summarize")
async def generate_summary(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    if article.has_summary:
        return {
            "success": True,
            "message": "文章已有摘要",
            "summary": article.summary
        }
    
    try:
        summary = await ai_service.summarize_single_article(db, article_id)
        
        if summary:
            return {
                "success": True,
                "summary": summary
            }
        else:
            raise HTTPException(status_code=500, detail="摘要生成失败")
            
    except ai_service.AISummaryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{article_id}/webhook")
async def send_to_webhook(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    
    try:
        success = webhook_service.send_webhook_notification(
            title=article.title,
            content=article.summary or article.description or "",
            url=article.link
        )
        
        return {
            "success": success,
            "message": "推送成功" if success else "推送失败"
        }
        
    except webhook_service.WebhookError as e:
        raise HTTPException(status_code=400, detail=str(e))

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl
import logging
from datetime import datetime

from app.models import get_db, RSSSource
from app.services import rss_service, webhook_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["RSS 源管理"])


class RSSSourceCreate(BaseModel):
    name: str
    url: HttpUrl
    description: Optional[str] = None


class RSSSourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class RSSSourceResponse(BaseModel):
    id: int
    name: str
    url: str
    description: Optional[str] = None
    enabled: bool
    last_fetched: Optional[str] = None
    fetch_error_count: int
    created_at: Optional[str] = None
    
    class Config:
        from_attributes = True


def serialize_source(source: RSSSource) -> dict:
    """序列化 RSS 源对象"""
    def format_datetime(dt):
        return dt.isoformat() if dt else None
    
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


@router.get("", response_model=List[RSSSourceResponse])
async def list_sources(
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    
    query = select(RSSSource)
    
    if enabled is not None:
        query = query.where(RSSSource.enabled == enabled)
    
    query = query.order_by(RSSSource.created_at.desc())
    
    result = await db.execute(query)
    sources = result.scalars().all()
    
    return [RSSSourceResponse(**serialize_source(s)) for s in sources]


@router.get("/{source_id}", response_model=RSSSourceResponse)
async def get_source(source_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    
    result = await db.execute(select(RSSSource).where(RSSSource.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="RSS 源不存在")
    
    return RSSSourceResponse(**serialize_source(source))


@router.post("", response_model=RSSSourceResponse, status_code=201)
async def create_source(item: RSSSourceCreate, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    
    try:
        existing = await db.execute(
            select(RSSSource).where(RSSSource.url == str(item.url))
        )
        existing_source = existing.scalar_one_or_none()
        
        if existing_source:
            raise HTTPException(status_code=400, detail="该 RSS 源已存在")
        
        test_result = rss_service.test_rss_connection(str(item.url))
        
        if not test_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"RSS 源连接失败: {test_result['message']}"
            )
        
        source = RSSSource(
            name=item.name,
            url=str(item.url),
            description=item.description,
            enabled=True
        )
        
        db.add(source)
        await db.commit()
        await db.refresh(source)
        
        logger.info(f"成功创建 RSS 源: {source.name} (ID: {source.id})")
        return RSSSourceResponse(**serialize_source(source))
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"创建 RSS 源失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建 RSS 源失败: {str(e)}")


@router.put("/{source_id}", response_model=RSSSourceResponse)
async def update_source(
    source_id: int,
    item: RSSSourceUpdate,
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import select
    
    result = await db.execute(select(RSSSource).where(RSSSource.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="RSS 源不存在")
    
    if item.name is not None:
        source.name = item.name
    if item.url is not None:
        source.url = str(item.url)
    if item.description is not None:
        source.description = item.description
    if item.enabled is not None:
        source.enabled = item.enabled
    
    await db.commit()
    await db.refresh(source)
    
    return RSSSourceResponse(**serialize_source(source))


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    
    result = await db.execute(select(RSSSource).where(RSSSource.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="RSS 源不存在")
    
    await db.delete(source)
    await db.commit()
    
    return None


@router.post("/{source_id}/toggle", response_model=RSSSourceResponse)
async def toggle_source(source_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    
    result = await db.execute(select(RSSSource).where(RSSSource.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="RSS 源不存在")
    
    source.enabled = not source.enabled
    await db.commit()
    await db.refresh(source)
    
    return RSSSourceResponse(**serialize_source(source))


@router.post("/{source_id}/fetch")
async def fetch_source(source_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from datetime import datetime
    
    result = await db.execute(select(RSSSource).where(RSSSource.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="RSS 源不存在")
    
    try:
        articles = rss_service.fetch_rss_feed(source)
        saved_count = await rss_service.save_articles(db, source_id, articles)
        
        source.last_fetched = datetime.utcnow()
        source.fetch_error_count = 0
        await db.commit()
        
        return {
            "success": True,
            "message": f"成功抓取 {len(articles)} 篇，保存 {saved_count} 篇新文章"
        }
        
    except rss_service.RSSFetchError as e:
        source.fetch_error_count += 1
        await db.commit()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"抓取 RSS 源失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"抓取失败: {str(e)}")


@router.get("/{source_id}/test")
async def test_source(source_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    
    result = await db.execute(select(RSSSource).where(RSSSource.id == source_id))
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(status_code=404, detail="RSS 源不存在")
    
    result = rss_service.test_rss_connection(source.url)
    
    return result

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models import get_db, KeywordConfig
from app.services import keyword_service

router = APIRouter(prefix="/api/keywords", tags=["关键词配置"])


class KeywordCreate(BaseModel):
    keyword: str
    enabled: bool = True


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    enabled: Optional[bool] = None


class KeywordResponse(BaseModel):
    id: int
    keyword: str
    enabled: bool
    match_count: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class KeywordTestResponse(BaseModel):
    keyword: str
    text: str
    is_match: bool
    matched_keywords: List[str]


def keyword_to_dict(keyword: KeywordConfig) -> dict:
    return {
        "id": keyword.id,
        "keyword": keyword.keyword,
        "enabled": keyword.enabled,
        "match_count": keyword.match_count,
        "created_at": keyword.created_at.isoformat() if keyword.created_at else None,
        "updated_at": keyword.updated_at.isoformat() if keyword.updated_at else None
    }


@router.get("", response_model=List[KeywordResponse])
async def list_keywords(
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(KeywordConfig)
    
    if enabled is not None:
        query = query.where(KeywordConfig.enabled == enabled)
    
    query = query.order_by(KeywordConfig.created_at.desc())
    
    result = await db.execute(query)
    keywords = result.scalars().all()
    
    return [KeywordResponse(**keyword_to_dict(kw)) for kw in keywords]


@router.get("/{keyword_id}", response_model=KeywordResponse)
async def get_keyword(keyword_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KeywordConfig).where(KeywordConfig.id == keyword_id))
    keyword = result.scalar_one_or_none()
    
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    
    return KeywordResponse(**keyword_to_dict(keyword))


@router.post("", response_model=KeywordResponse, status_code=201)
async def create_keyword(item: KeywordCreate, db: AsyncSession = Depends(get_db)):
    keyword_text = item.keyword.strip().lower()
    
    if not keyword_text:
        raise HTTPException(status_code=400, detail="关键词不能为空")
    
    result = await db.execute(
        select(KeywordConfig).where(KeywordConfig.keyword == keyword_text)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="该关键词已存在")
    
    keyword = KeywordConfig(
        keyword=keyword_text,
        enabled=item.enabled,
        match_count=0
    )
    
    db.add(keyword)
    await db.commit()
    await db.refresh(keyword)
    
    return KeywordResponse(**keyword_to_dict(keyword))


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    item: KeywordUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(KeywordConfig).where(KeywordConfig.id == keyword_id))
    keyword = result.scalar_one_or_none()
    
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    
    if item.keyword is not None:
        new_keyword_text = item.keyword.strip().lower()
        
        if new_keyword_text != keyword.keyword:
            check_result = await db.execute(
                select(KeywordConfig).where(
                    KeywordConfig.keyword == new_keyword_text,
                    KeywordConfig.id != keyword_id
                )
            )
            existing = check_result.scalar_one_or_none()
            
            if existing:
                raise HTTPException(status_code=400, detail="该关键词已存在")
        
        keyword.keyword = new_keyword_text
    
    if item.enabled is not None:
        keyword.enabled = item.enabled
    
    await db.commit()
    await db.refresh(keyword)
    
    return KeywordResponse(**keyword_to_dict(keyword))


@router.delete("/{keyword_id}", status_code=204)
async def delete_keyword(keyword_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KeywordConfig).where(KeywordConfig.id == keyword_id))
    keyword = result.scalar_one_or_none()
    
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    
    await db.delete(keyword)
    await db.commit()
    
    return None


@router.post("/{keyword_id}/toggle", response_model=KeywordResponse)
async def toggle_keyword(keyword_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KeywordConfig).where(KeywordConfig.id == keyword_id))
    keyword = result.scalar_one_or_none()
    
    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")
    
    keyword.enabled = not keyword.enabled
    await db.commit()
    await db.refresh(keyword)
    
    return KeywordResponse(**keyword_to_dict(keyword))


@router.post("/test", response_model=KeywordTestResponse)
async def test_keyword_match(
    keyword: str = Query(..., description="要测试的关键词"),
    text: str = Query(..., description="测试文本")
):
    is_match, matched_keywords, _ = keyword_service.test_keyword_match(keyword, text)
    
    return {
        "keyword": keyword,
        "text": text,
        "is_match": is_match,
        "matched_keywords": matched_keywords
    }


@router.post("/apply-filter")
async def apply_keyword_filter(db: AsyncSession = Depends(get_db)):
    filtered_ids = await keyword_service.filter_articles_by_keywords(db)
    
    return {
        "success": True,
        "filtered_count": len(filtered_ids)
    }


@router.post("/bulk-delete")
async def bulk_delete_keywords(ids: List[int], db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(KeywordConfig).where(KeywordConfig.id.in_(ids))
    )
    keywords = result.scalars().all()
    
    deleted = len(keywords)
    for keyword in keywords:
        await db.delete(keyword)
    
    await db.commit()
    
    return {
        "success": True,
        "deleted_count": deleted
    }

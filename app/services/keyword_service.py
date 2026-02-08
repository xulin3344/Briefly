import re
from typing import List, Set, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models import Article, KeywordConfig


class KeywordFilter:
    
    def __init__(self, keywords: Optional[List[str]] = None, min_length: int = 2):
        self._keywords: Set[str] = set()
        self._patterns: List[re.Pattern] = []
        self._original_keywords: List[str] = []
        self._min_length = min_length
        
        if keywords:
            self.add_keywords(keywords)
    
    def add_keywords(self, keywords: List[str]):
        for keyword in keywords:
            if keyword and keyword.strip():
                keyword_clean = keyword.strip()
                
                if len(keyword_clean) < self._min_length:
                    continue
                    
                escaped = re.escape(keyword_clean)
                self._keywords.add(keyword_clean.lower())
                self._original_keywords.append(keyword_clean)
                
                pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
                self._patterns.append(pattern)
    
    def clear(self):
        self._keywords.clear()
        self._patterns.clear()
        self._original_keywords.clear()
    
    def matches(self, text: str) -> Tuple[bool, List[str], bool]:
        if not text or not self._patterns:
            return False, [], False
        
        text_lower = text.lower()
        matched = []
        title_match = False
        
        for i, pattern in enumerate(self._patterns):
            if pattern.search(text):
                matched.append(list(self._keywords)[i])
        
        if len(matched) > 0:
            return True, matched, title_match
        
        return False, [], False
    
    def filter_articles(self, articles: List[Article]) -> Tuple[List[Article], List[Article]]:
        matched = []
        unmatched = []
        
        for article in articles:
            title = article.title or ''
            description = article.description or ''
            content = article.content or ''
            
            text_to_check = f"{title} {description} {content}"
            is_match, _, _ = self.matches(text_to_check)
            
            if is_match:
                matched.append(article)
            else:
                unmatched.append(article)
        
        return matched, unmatched
    
    @property
    def keyword_count(self) -> int:
        return len(self._keywords)


async def load_keywords_from_db(db: AsyncSession) -> List[str]:
    result = await db.execute(
        select(KeywordConfig).where(KeywordConfig.enabled == True)
    )
    keywords = result.scalars().all()
    
    return [kw.keyword for kw in keywords]


async def create_filter_from_db(db: AsyncSession) -> KeywordFilter:
    keywords = await load_keywords_from_db(db)
    return KeywordFilter(keywords)


async def update_keyword_match_count(db: AsyncSession, keyword: str, count: int = 1):
    result = await db.execute(
        select(KeywordConfig).where(
            KeywordConfig.keyword == keyword,
            KeywordConfig.enabled == True
        )
    )
    keyword_config = result.scalar_one_or_none()
    
    if keyword_config:
        keyword_config.match_count += count
        await db.commit()


async def filter_articles_by_keywords(db: AsyncSession, article_ids: Optional[List[int]] = None) -> List[int]:
    keyword_filter = await create_filter_from_db(db)
    
    if keyword_filter.keyword_count == 0:
        return []
    
    query = select(Article).where(Article.is_filtered == False)
    
    if article_ids:
        query = query.where(Article.id.in_(article_ids))
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    matched_articles, _ = keyword_filter.filter_articles(articles)
    
    filtered_ids = []
    for article in matched_articles:
        article.is_filtered = True
        filtered_ids.append(article.id)
        
        text_to_check = f"{article.title} {article.description or ''} {article.content or ''}"
        _, matched_keywords, _ = keyword_filter.matches(text_to_check)
        
        for keyword in matched_keywords:
            await update_keyword_match_count(db, keyword)
    
    await db.commit()
    
    return filtered_ids


async def get_filtered_articles(db: AsyncSession, limit: int = 50, offset: int = 0) -> List[Article]:
    result = await db.execute(
        select(Article)
        .where(Article.is_filtered == True)
        .order_by(Article.published_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_unfiltered_articles(db: AsyncSession, limit: int = 50, offset: int = 0) -> List[Article]:
    result = await db.execute(
        select(Article)
        .where(Article.is_filtered == False)
        .order_by(Article.published_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def check_keyword_exists(db: AsyncSession, keyword: str) -> bool:
    result = await db.execute(
        select(KeywordConfig).where(KeywordConfig.keyword == keyword.lower().strip())
    )
    exists = result.scalar_one_or_none()
    return exists is not None


def test_keyword_match(keyword: str, text: str) -> tuple:
    filter_obj = KeywordFilter([keyword])
    return filter_obj.matches(text)

from typing import Optional, List
from openai import OpenAI, AsyncOpenAI, APIError, RateLimitError
import httpx
import logging
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings, ZHIPUAI_BASE_URL
from app.models import Article, AISettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AISummaryError(Exception):
    pass


class APIKeyMissingError(AISummaryError):
    pass


class APIRateLimitError(AISummaryError):
    pass


class APITimeoutError(AISummaryError):
    pass


class APIGenericError(AISummaryError):
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def get_ai_settings(db: AsyncSession) -> AISettings:
    result = await db.execute(select(AISettings).where(AISettings.id == 1))
    settings_record = result.scalar_one_or_none()
    
    if not settings_record:
        settings_record = AISettings(id=1)
        db.add(settings_record)
        await db.commit()
        await db.refresh(settings_record)
    
    return settings_record


async def get_async_ai_client_from_settings(db: AsyncSession) -> tuple[Optional[AsyncOpenAI], AISettings]:
    ai_settings = await get_ai_settings(db)
    
    api_key = ai_settings.api_key or settings.ZHIPUAI_API_KEY or settings.OPENAI_API_KEY
    base_url = ai_settings.base_url or ZHIPUAI_BASE_URL
    
    if not api_key:
        return None, ai_settings
    
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url if base_url else None
    )
    
    return client, ai_settings


def get_openai_client() -> Optional[OpenAI]:
    api_key = settings.ZHIPUAI_API_KEY or settings.OPENAI_API_KEY
    base_url = ZHIPUAI_BASE_URL
    
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key, base_url=base_url if base_url else None)


async def get_ai_config(db: AsyncSession) -> dict:
    ai_settings = await get_ai_settings(db)
    
    return {
        "model": ai_settings.model or settings.AI_MODEL or "glm-4",
        "max_summary_length": ai_settings.max_summary_length or settings.MAX_SUMMARY_LENGTH or 100,
        "base_url": ai_settings.base_url or ZHIPUAI_BASE_URL,
        "has_api_key": bool(ai_settings.api_key or settings.ZHIPUAI_API_KEY or settings.OPENAI_API_KEY),
        "enabled": ai_settings.enabled
    }


async def save_ai_settings(
    db: AsyncSession,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    max_summary_length: Optional[int] = None,
    enabled: Optional[bool] = None
) -> AISettings:
    ai_settings = await get_ai_settings(db)
    
    if api_key is not None:
        ai_settings.api_key = api_key
    if base_url is not None:
        ai_settings.base_url = base_url.strip() if base_url.strip() else None
    if model is not None:
        ai_settings.model = model
    if max_summary_length is not None:
        ai_settings.max_summary_length = max_summary_length
    if enabled is not None:
        ai_settings.enabled = enabled
    
    await db.commit()
    await db.refresh(ai_settings)
    
    logger.info("AI 设置已更新")
    return ai_settings


async def validate_api_key(db: AsyncSession) -> tuple[bool, str]:
    ai_settings = await get_ai_settings(db)
    
    api_key = ai_settings.api_key or settings.ZHIPUAI_API_KEY or settings.OPENAI_API_KEY
    base_url = ai_settings.base_url or ZHIPUAI_BASE_URL
    
    if not api_key:
        return False, "API Key 未配置"
    
    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url if base_url else None)
        
        test_response = await client.chat.completions.create(
            model=ai_settings.model or settings.AI_MODEL or "glm-4",
            messages=[{"role": "user", "content": "测试"}],
            max_tokens=10
        )
        
        if test_response:
            return True, "API Key 有效"
        else:
            return False, "API 调用返回空响应"
            
    except APIError as e:
        error_msg = str(e)
        if "invalid_api_key" in error_msg:
            return False, "API Key 无效"
        elif "rate_limit" in error_msg.lower():
            return False, "触发速率限制"
        else:
            return False, f"API 错误: {error_msg[:100]}"
    except httpx.TimeoutException:
        return False, "API 请求超时"
    except Exception as e:
        return False, f"验证失败: {str(e)[:100]}"


def truncate_text(text: str, max_chars: int = 8000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def generate_summary_prompt(title: str, content: str) -> str:
    truncated_content = truncate_text(content, max_chars=4000)
    
    prompt = f"""
请用中文简洁地总结以下文章，摘要字数控制在 100 字以内：

标题：{title}

内容：
{truncated_content}

请直接输出摘要，不需要任何前缀或格式。
"""
    return prompt


async def summarize_article_async(
    title: str,
    content: str,
    db: AsyncSession,
    client: Optional[AsyncOpenAI] = None
) -> Optional[str]:
    if client is None:
        client, ai_settings = await get_async_ai_client_from_settings(db)
    
    if client is None:
        raise APIKeyMissingError("AI API Key 未配置")
    
    ai_settings = await get_ai_settings(db)
    model = ai_settings.model or settings.AI_MODEL or "glm-4"
    max_length = ai_settings.max_summary_length or settings.MAX_SUMMARY_LENGTH or 100
    
    prompt = generate_summary_prompt(title, content)
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.5,
            timeout=30
        )
        
        summary = response.choices[0].message.content.strip()
        
        if len(summary) > max_length + 50:
            summary = summary[:max_length] + "..."
        
        logger.info(f"成功生成摘要: {summary[:50]}...")
        return summary
        
    except RateLimitError:
        raise APIRateLimitError("API 速率限制，请稍后重试")
    except httpx.TimeoutException:
        raise APITimeoutError("API 调用超时")
    except APIError as e:
        raise APIGenericError(f"API 调用失败: {str(e)}")


async def summarize_single_article(db: AsyncSession, article_id: int) -> Optional[str]:
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    
    if not article:
        return None
    
    if article.has_summary:
        return article.summary
    
    if not article.content or len(article.content) < 50:
        logger.warning(f"文章内容太短，无法生成摘要: {article.id}")
        return None
    
    try:
        summary = await summarize_article_async(
            article.title,
            article.content,
            db
        )
        
        if summary:
            article.summary = summary
            article.has_summary = True
            await db.commit()
        
        return summary
        
    except AISummaryError as e:
        logger.error(f"摘要生成失败: {article.id}, 错误: {str(e)}")
        return None


async def generate_test_summary(db: AsyncSession) -> tuple[bool, str]:
    test_title = "人工智能技术的最新发展趋势"
    test_content = "人工智能技术在过去一年取得了显著进展。"
    
    try:
        summary = await summarize_article_async(test_title, test_content, db)
        if summary:
            return True, summary
        return False, "生成失败：返回空结果"
    except AISummaryError as e:
        return False, str(e)


async def summarize_articles_batch(
    articles: List[Article],
    db: AsyncSession,
    max_concurrent: int = 5
) -> int:
    articles_to_summarize = [
        a for a in articles
        if not a.has_summary and a.content and len(a.content) > 50
    ]
    
    if not articles_to_summarize:
        return 0
    
    client, _ = await get_async_ai_client_from_settings(db)
    
    if client is None:
        logger.warning("无法生成摘要：AI API Key 未配置")
        return 0
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def summarize_with_limit(article: Article):
        async with semaphore:
            try:
                summary = await summarize_article_async(
                    article.title,
                    article.content,
                    db,
                    client
                )
                
                if summary:
                    article.summary = summary
                    article.has_summary = True
                    return True
                return False
                
            except AISummaryError as e:
                logger.error(f"文章摘要生成失败: {article.id}, 错误: {str(e)}")
                return False
    
    tasks = [summarize_with_limit(a) for a in articles_to_summarize]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    
    await db.commit()
    
    logger.info(f"批量摘要完成: {success_count}/{len(articles_to_summarize)}")
    return success_count


def summarize_article(title: str, content: str) -> Optional[str]:
    """同步生成文章摘要（向后兼容）"""
    import asyncio
    
    async def _summarize():
        async with AsyncSessionLocal() as db:
            return await summarize_article_async(title, content, db)
    
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_summarize())
    finally:
        loop.close()

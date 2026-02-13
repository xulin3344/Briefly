from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models import Article, AIFilterConfig, AISettings
from app.services import ai_service
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIFilterError(Exception):
    pass


async def get_ai_filter_config(db: AsyncSession) -> AIFilterConfig:
    result = await db.execute(select(AIFilterConfig).where(AIFilterConfig.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = AIFilterConfig(id=1, enabled=False, filter_prompt="", auto_apply=True)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    
    return config


async def save_ai_filter_config(
    db: AsyncSession,
    enabled: bool = None,
    filter_prompt: str = None,
    auto_apply: bool = None
) -> AIFilterConfig:
    config = await get_ai_filter_config(db)
    
    if enabled is not None:
        config.enabled = enabled
    if filter_prompt is not None:
        config.filter_prompt = filter_prompt
    if auto_apply is not None:
        config.auto_apply = auto_apply
    
    await db.commit()
    await db.refresh(config)
    
    logger.info(f"AI 过滤配置已更新: enabled={config.enabled}")
    return config


async def filter_articles_by_ai(db: AsyncSession) -> Dict:
    """
    使用 AI 智能筛选文章
    根据用户配置的筛选提示词，保留符合提示词的文章，其他标记为AI过滤
    """
    config = await get_ai_filter_config(db)
    
    if not config.enabled:
        return {
            "status": "skipped",
            "message": "AI 智能筛选未启用"
        }
    
    if not config.filter_prompt or not config.filter_prompt.strip():
        return {
            "status": "error",
            "message": "请配置筛选提示词"
        }
    
    client, ai_settings = await ai_service.get_async_ai_client_from_settings(db)
    
    if not client:
        return {
            "status": "error",
            "message": "AI 未配置，请先在 AI 设置中配置 API Key"
        }
    
    result = await db.execute(
        select(Article).order_by(Article.published_at.desc()).limit(100)
    )
    articles = result.scalars().all()
    
    # 首先清空所有之前的AI过滤标记
    await db.execute(
        Article.__table__.update().values(is_ai_filtered=False)
    )
    await db.commit()
    
    if not articles:
        return {
            "status": "success",
            "message": "没有需要筛选的文章",
            "filtered_count": 0
        }
    
    articles_data = []
    for article in articles:
        articles_data.append({
            "id": article.id,
            "title": article.title,
            "description": article.description or "",
            "link": article.link
        })
    
    prompt = f"""请根据以下筛选规则判断每篇文章是否符合要求。

筛选规则（保留符合这些规则的文章，不符合的标记为过滤）：
{config.filter_prompt}

文章列表：
"""
    for i, art in enumerate(articles_data, 1):
        prompt += f"{i}. 标题：{art['title']}\n   描述：{art['description'][:200] if art['description'] else '无'}\n\n"
    
    prompt += """请按以下 JSON 格式返回需要保留的文章ID列表（即符合筛选条件的文章），只返回ID列表，不要其他内容：
{"keep_ids": [文章ID列表]}

只返回符合筛选条件的文章ID，这些文章将保留在主列表中。其他文章将被标记为AI过滤。如果都符合条件则返回全部ID。"""

    try:
        model = ai_settings.model or "glm-4"
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个文章筛选助手，负责根据用户提供的规则判断文章是否符合要求。符合要求的保留，不符合的标记为过滤。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        
        import json
        import re
        
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        
        if json_match:
            result_dict = json.loads(json_match.group())
            keep_ids = result_dict.get("keep_ids", [])
        else:
            logger.warning(f"AI 返回格式异常: {result_text}")
            keep_ids = []
        
        keep_id_set = set([int(id) for id in keep_ids if str(id).isdigit()])
        
        filtered_count = 0
        for article in articles:
            if article.id in keep_id_set:
                article.is_ai_filtered = False
            else:
                if not article.is_ai_filtered:
                    filtered_count += 1
                article.is_ai_filtered = True
        
        await db.commit()
        
        logger.info(f"AI 智能筛选完成: 标记 {filtered_count} 篇文章为AI过滤")
        
        return {
            "status": "success",
            "message": f"已筛选 {filtered_count} 篇文章到AI过滤栏",
            "filtered_count": filtered_count
        }
            
    except Exception as e:
        logger.error(f"AI 筛选失败: {str(e)}")
        return {
            "status": "error",
            "message": f"AI 筛选失败: {str(e)}"
        }


async def run_ai_filter(db: AsyncSession) -> Dict:
    """
    运行 AI 筛选任务（供调度器调用）
    """
    logger.info("=" * 50)
    logger.info(f"[{datetime.now()}] 开始执行 AI 智能筛选任务")
    
    try:
        result = await filter_articles_by_ai(db)
        
        config = await get_ai_filter_config(db)
        config.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"AI 筛选任务异常: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

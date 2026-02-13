from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import get_db, WebhookConfig, Article
from app.services import webhook_service
from app.core.logging import get_logger

try:
    from app.services.webhook_scheduler import update_webhook_schedule
except ImportError:
    update_webhook_schedule = None

router = APIRouter(prefix="/api/webhook", tags=["Webhook 配置"])
logger = get_logger(__name__)


class WebhookConfigResponse(BaseModel):
    """Webhook 配置响应模型"""
    id: int
    enabled: bool
    url: Optional[str]
    platform: str
    name: Optional[str]
    description: Optional[str]
    schedule_enabled: bool
    schedule_frequency: str
    schedule_time: str
    schedule_day_of_week: int
    schedule_day_of_month: int
    push_favorites: bool
    push_filtered: bool
    
    class Config:
        from_attributes = True


class WebhookConfigUpdate(BaseModel):
    """Webhook 配置更新模型"""
    enabled: Optional[bool] = None
    url: Optional[str] = Field(None, max_length=500)
    platform: Optional[str] = Field(None, pattern="^(wecom|dingtalk|feishu|feishu-card|feishu-flow|generic)$")
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    schedule_enabled: Optional[bool] = None
    schedule_frequency: Optional[str] = Field(None, pattern="^(hourly|daily|weekly|monthly)$")
    schedule_time: Optional[str] = Field(None, pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    schedule_day_of_week: Optional[int] = Field(None, ge=1, le=7)
    schedule_day_of_month: Optional[int] = Field(None, ge=1, le=28)
    push_favorites: Optional[bool] = None
    push_filtered: Optional[bool] = None


async def get_or_create_webhook_config(db: AsyncSession) -> WebhookConfig:
    """获取或创建 Webhook 配置"""
    result = await db.execute(select(WebhookConfig).where(WebhookConfig.id == 1))
    config = result.scalar_one_or_none()
    
    if not config:
        config = WebhookConfig(id=1, enabled=False, platform="generic")
        db.add(config)
        await db.commit()
        await db.refresh(config)
        logger.info("创建默认 Webhook 配置")
    
    return config


@router.get("/config", response_model=WebhookConfigResponse)
async def get_webhook_config(db: AsyncSession = Depends(get_db)):
    """
    获取 Webhook 配置
    
    Returns:
        Webhook 配置信息
    """
    config = await get_or_create_webhook_config(db)
    return config


@router.post("/config", response_model=WebhookConfigResponse)
async def update_webhook_config(
    settings: WebhookConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新 Webhook 配置
    
    Args:
        settings: 配置更新数据
        db: 数据库会话
        
    Returns:
        更新后的配置
    """
    config = await get_or_create_webhook_config(db)
    
    if settings.enabled is not None:
        config.enabled = settings.enabled
    if settings.url is not None:
        config.url = settings.url.strip() if settings.url.strip() else None
    if settings.platform is not None:
        config.platform = settings.platform
    if settings.name is not None:
        config.name = settings.name.strip() if settings.name.strip() else None
    if settings.description is not None:
        config.description = settings.description.strip() if settings.description.strip() else None
    
    # 定时推送配置
    if settings.schedule_enabled is not None:
        config.schedule_enabled = settings.schedule_enabled
    if settings.schedule_frequency is not None:
        config.schedule_frequency = settings.schedule_frequency
    if settings.schedule_time is not None:
        config.schedule_time = settings.schedule_time
    if settings.schedule_day_of_week is not None:
        config.schedule_day_of_week = settings.schedule_day_of_week
    if settings.schedule_day_of_month is not None:
        config.schedule_day_of_month = settings.schedule_day_of_month
    if settings.push_favorites is not None:
        config.push_favorites = settings.push_favorites
    if settings.push_filtered is not None:
        config.push_filtered = settings.push_filtered
    
    await db.commit()
    await db.refresh(config)
    
    # 更新定时任务
    if update_webhook_schedule:
        try:
            update_webhook_schedule()
        except Exception as e:
            logger.error(f"更新定时任务失败: {str(e)}")
    
    logger.info(f"Webhook 配置已更新: enabled={config.enabled}, platform={config.platform}, schedule_enabled={config.schedule_enabled}")
    return config


@router.post("/test")
async def test_webhook_config(
    db: AsyncSession = Depends(get_db),
    body: Optional[dict] = Body(None)
) -> dict:
    """
    测试 Webhook 配置
    即使未启用也可以测试
    
    Args:
        body: 可选的请求体，包含 url 和 platform（用于测试前端输入的配置）
        
    Returns:
        测试结果
    """
    # 获取测试参数，优先使用请求体中的值
    test_url = None
    test_platform = None
    
    if body:
        test_url = body.get('url')
        test_platform = body.get('platform')
    
    config = await get_or_create_webhook_config(db)
    
    # 使用请求体中的参数，否则使用数据库配置
    target_url = test_url or config.url
    target_platform = test_platform or config.platform
    
    if not target_url:
        return {
            "success": False,
            "message": "请先配置 Webhook URL"
        }
    
    try:
        result = webhook_service.send_webhook_notification(
            title="Briefly 测试通知",
            content="这是一条测试通知，用于验证 Webhook 配置是否正确。如果收到此消息，说明配置成功！",
            webhook_url=target_url,
            platform=target_platform
        )
        
        return {
            "success": result,
            "message": "测试通知发送成功" if result else "测试通知发送失败，请检查 URL 和网络连接"
        }
        
    except webhook_service.WebhookError as e:
        logger.error(f"Webhook 测试失败: {str(e)}")
        return {
            "success": False,
            "message": f"推送失败: {str(e)}"
        }
    except Exception as e:
        logger.exception(f"Webhook 测试异常: {str(e)}")
        return {
            "success": False,
            "message": f"推送异常: {str(e)}"
        }


@router.post("/push-favorites")
async def push_favorites(
    db: AsyncSession = Depends(get_db)
):
    """
    推送所有收藏文章
    按标题+链接列表形式推送
    
    Returns:
        推送结果
    """
    config = await get_or_create_webhook_config(db)
    
    if not config.enabled or not config.url:
        return {
            "success": False,
            "message": "Webhook 未启用或 URL 未配置"
        }
    
    result = await db.execute(
        select(Article).where(Article.is_favorite == True).order_by(Article.published_at.desc())
    )
    favorites = result.scalars().all()
    
    if not favorites:
        return {
            "success": False,
            "message": "没有收藏的文章"
        }
    
    articles = [{"title": a.title, "link": a.link} for a in favorites]
    
    try:
        message = webhook_service.build_favorites_webhook_message(articles, config.platform)
        
        success = webhook_service.send_webhook_message(config.url, message)
        
        return {
            "success": success,
            "message": f"成功推送 {len(favorites)} 篇收藏文章" if success else "推送失败"
        }
        
    except webhook_service.WebhookError as e:
        logger.error(f"收藏文章推送失败: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@router.post("/push-filtered")
async def push_filtered(
    db: AsyncSession = Depends(get_db)
):
    """
    推送所有过滤文章
    
    Returns:
        推送结果
    """
    config = await get_or_create_webhook_config(db)
    
    if not config.enabled or not config.url:
        return {
            "success": False,
            "message": "Webhook 未启用或 URL 未配置"
        }
    
    result = await db.execute(
        select(Article).where(Article.is_filtered == True).order_by(Article.published_at.desc())
    )
    filtered_articles = result.scalars().all()
    
    if not filtered_articles:
        return {
            "success": False,
            "message": "没有过滤的文章"
        }
    
    articles = [{"title": a.title, "link": a.link} for a in filtered_articles]
    
    try:
        message = webhook_service.build_favorites_webhook_message(articles, config.platform)
        
        success = webhook_service.send_webhook_message(config.url, message)
        
        return {
            "success": success,
            "message": f"成功推送 {len(filtered_articles)} 篇过滤文章" if success else "推送失败"
        }
        
    except webhook_service.WebhookError as e:
        logger.error(f"过滤文章推送失败: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

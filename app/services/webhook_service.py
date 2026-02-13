from typing import Dict, List, Optional
import json
import httpx

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WebhookError(Exception):
    """Webhook 异常基类"""
    pass


class WebhookConfigError(WebhookError):
    """Webhook 配置错误"""
    pass


class WebhookSendError(WebhookError):
    """Webhook 发送失败"""
    pass


def send_webhook_notification(
    title: str,
    content: str,
    url: Optional[str] = None,
    webhook_url: Optional[str] = None,
    platform: str = "generic"
) -> bool:
    """
    发送 Webhook 通知
    支持企业微信、钉钉、飞书等 Webhook 格式
    
    Args:
        title: 通知标题
        content: 通知内容
        url: 跳转链接（可选）
        webhook_url: Webhook URL，如果不提供则使用环境变量配置
        platform: 平台类型 (wecom, dingtalk, feishu, generic)
        
    Returns:
        True 表示发送成功
    """
    # 获取 Webhook URL，优先使用传入的参数
    target_url = webhook_url or settings.WEBHOOK_URL
    if not target_url:
        logger.error("Webhook URL 未配置")
        raise WebhookConfigError("Webhook URL 未配置")
    
    # 根据平台构建消息格式
    message = build_webhook_message_by_platform(title, content, url, platform)
    
    try:
        # 发送 HTTP POST 请求
        with httpx.Client(timeout=30) as client:
            response = client.post(target_url, json=message)
            response.raise_for_status()
        
        logger.info(f"Webhook 通知发送成功: {title} ({platform})")
        return True
        
    except httpx.TimeoutException:
        logger.error("Webhook 请求超时")
        raise WebhookSendError("请求超时")
    except httpx.ConnectError as e:
        logger.error(f"Webhook 连接失败: {str(e)}")
        raise WebhookSendError(f"连接失败: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Webhook HTTP 错误: {e.response.status_code}")
        raise WebhookSendError(f"HTTP 错误: {e.response.status_code}")


def build_webhook_message_by_platform(
    title: str,
    content: str,
    url: Optional[str] = None,
    platform: str = "generic"
) -> Dict:
    """
    根据平台构建 Webhook 消息格式
    
    Args:
        title: 消息标题
        content: 消息内容
        url: 跳转链接
        platform: 平台类型 (wecom, dingtalk, feishu, feishu-card, feishu-flow, generic)
        
    Returns:
        适配各平台的消息格式
    """
    if platform == "feishu-card":
        return build_feishu_card_message(title, content, url)
    elif platform == "feishu":
        return build_feishu_flow_message(title, content, url)
    elif platform == "wecom":
        return build_wecom_message(title, content, url)
    elif platform == "dingtalk":
        return build_dingtalk_message(title, content, url)
    elif platform == "feishu-flow":
        return build_feishu_flow_message(title, content, url)
    else:
        return build_generic_message(title, content, url)


def send_enterprise_wechat_notification(
    title: str,
    content: str,
    url: Optional[str] = None
) -> bool:
    """
    发送企业微信 Webhook 通知
    
    Args:
        title: 通知标题
        content: 通知内容
        url: 文章链接
        
    Returns:
        True 表示发送成功
    """
    if not settings.WEBHOOK_URL:
        logger.error("企业微信 Webhook URL 未配置")
        return False
    
    # 企业微信 Markdown 格式
    url_part = f'<div class="normal">[查看原文]({url})</div>' if url else ""
    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""<div class="gray">Briefly 摘要</div>
<div class="normal">{title}</div>
<div class="quote">{content}</div>
{url_part}
"""
        }
    }
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(settings.WEBHOOK_URL, json=message)
            response.raise_for_status()
        
        return True
        
    except Exception as e:
        logger.error(f"企业微信通知失败: {str(e)}")
        return False


def send_dingtalk_notification(
    title: str,
    content: str,
    url: Optional[str] = None
) -> bool:
    """
    发送钉钉 Webhook 通知
    
    Args:
        title: 通知标题
        content: 通知内容
        url: 文章链接
        
    Returns:
        True 表示发送成功
    """
    if not settings.WEBHOOK_URL:
        logger.error("钉钉 Webhook URL 未配置")
        return False
    
    # 钉钉 Markdown 格式
    url_part = f"[查看原文]({url})" if url else ""
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"""## {title}

{content}

{url_part}
"""
        }
    }
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(settings.WEBHOOK_URL, json=message)
            response.raise_for_status()
        
        return True
        
    except Exception as e:
        logger.error(f"钉钉通知失败: {str(e)}")
        return False


def test_webhook_connection() -> Dict:
    """
    测试 Webhook 连接（使用数据库配置）
    
    Returns:
        测试结果字典
    """
    from app.models import get_db, WebhookConfig
    from sqlalchemy import select
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        result = db.execute(select(WebhookConfig).where(WebhookConfig.id == 1))
        config = result.scalar_one_or_none()
        
        if not config or not config.enabled or not config.url:
            return {
                "success": False,
                "message": "Webhook 未配置"
            }
        
        try:
            success = send_webhook_notification(
                title="Briefly 测试通知",
                content="这是一条测试通知，用于验证 Webhook 配置是否正确。",
                webhook_url=config.url,
                platform=config.platform
            )
            
            return {
                "success": success,
                "message": "通知发送成功" if success else "通知发送失败"
            }
        except WebhookSendError as e:
            return {
                "success": False,
                "message": str(e)
            }
    finally:
        db.close()
    
    try:
        success = send_webhook_notification(
            title="Briefly 测试通知",
            content="这是一条测试通知，用于验证 Webhook 配置是否正确。"
        )
        
        return {
            "success": success,
            "message": "测试通知发送成功" if success else "测试通知发送失败"
        }
        
    except WebhookError as e:
        return {
            "success": False,
            "message": str(e)
        }


def build_feishu_flow_message(
    title: str,
    content: str,
    url: Optional[str] = None
) -> Dict:
    """
    构建飞书群机器人消息格式（简洁版）
    适用于飞书自定义机器人
    使用 text 格式
    """
    url_part = f"\n\n查看原文: {url}" if url else ""
    
    message = {
        "msg_type": "text",
        "content": {
            "text": f"{title}\n\n{content[:400]}{'...' if len(content) > 400 else ''}{url_part}"
        }
    }
    
    return message


def build_feishu_card_message(
    title: str,
    content: str,
    url: Optional[str] = None
) -> Dict:
    """
    构建飞书群机器人卡片消息格式
    适用于飞书自定义机器人的富文本卡片
    """
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content[:500] + ("..." if len(content) > 500 else "")
            }
        }
    ]
    
    if url:
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "lark_md", "content": "查看原文"},
                    "type": "primary",
                    "url": url
                }
            ]
        })
    
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "lark_md",
                    "content": title[:100]
                },
                "template": "blue"
            },
            "elements": elements
        }
    }
    
    return message


def build_generic_message(
    title: str,
    content: str,
    url: Optional[str] = None
) -> Dict:
    """
    构建通用 Markdown 格式消息
    适用于未指定平台的情况
    """
    url_part = f"\n\n<a href=\"{url}\">查看原文</a>" if url else ""
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"**{title}**\n\n{content}{url_part}"
        }
    }
    return message


def build_wecom_message(
    title: str,
    content: str,
    url: Optional[str] = None
) -> Dict:
    """构建企业微信消息"""
    url_part = f'<div class="normal">[查看原文]({url})</div>' if url else ""
    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""<div class="gray">Briefly 摘要</div>
<div class="normal">{title}</div>
<div class="quote">{content[:500]}</div>
{url_part}
"""
        }
    }
    return message


def build_dingtalk_message(
    title: str,
    content: str,
    url: Optional[str] = None
) -> Dict:
    """构建钉钉消息"""
    url_part = f"[查看原文]({url})" if url else ""
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"## {title}\n\n{content[:500]}\n\n{url_part}"
        }
    }
    return message


def send_webhook_message(webhook_url: str, message: Dict) -> bool:
    """发送 Webhook 消息"""
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(webhook_url, json=message)
            response.raise_for_status()
            
            # 检查飞书响应
            try:
                resp_data = response.json()
                if resp_data.get("code") and resp_data.get("code") != 0:
                    error_msg = resp_data.get("msg", "Unknown error")
                    logger.error(f"Webhook 发送失败: {error_msg}")
                    return False
            except:
                pass
                
        return True
    except Exception as e:
        logger.error(f"Webhook 发送失败: {str(e)}")
        return False


def build_favorites_webhook_message(
    articles: list,
    platform: str = "feishu"
) -> Dict:
    """构建收藏文章批量推送消息"""
    if platform in ("feishu", "feishu-card"):
        return build_feishu_favorites_message(articles)
    elif platform == "feishu-flow":
        return build_feishu_flow_favorites_message(articles)
    elif platform == "wecom":
        return build_wecom_favorites_message(articles)
    elif platform == "dingtalk":
        return build_dingtalk_favorites_message(articles)
    else:
        return build_generic_favorites_message(articles)


def build_feishu_favorites_message(articles: list) -> Dict:
    """构建飞书收藏文章批量推送消息 - 卡片格式"""
    elements = []
    
    # 添加标题
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"📚 **收藏文章 ({len(articles)} 篇)**"
        }
    })
    
    for i, article in enumerate(articles[:10], 1):  # 最多显示10篇
        title = article.get('title', '')
        link = article.get('link', '')
        
        # 完整标题，使用div+超链接格式
        content = f"**{i}.** [{title}]({link})" if link else f"**{i}.** {title}"
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content
            }
        })
    
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "lark_md",
                    "content": "📚 收藏文章推送"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }
    
    return message


def build_feishu_flow_favorites_message(articles: list) -> Dict:
    """构建飞书 Flow 收藏文章批量推送消息"""
    # Build text content with all articles
    lines = [f"收藏文章 ({len(articles)} 篇)\n"]
    for i, article in enumerate(articles, 1):
        title = article.get('title', '')
        link = article.get('link', '')
        lines.append(f"{i}. {title}")
        if link:
            lines.append(f"   {link}")
    
    message = {
        "msg_type": "text",
        "content": {
            "text": "\n".join(lines)
        }
    }
    
    return message


def build_wecom_favorites_message(articles: list) -> Dict:
    """构建企业微信收藏文章批量推送消息"""
    content_lines = [f"📚 收藏文章 ({len(articles)} 篇)\n"]
    
    for i, article in enumerate(articles, 1):
        title = article.get('title', '')
        link = article.get('link', '')
        
        if link:
            content_lines.append(f"{i}. [{title}]({link})")
        else:
            content_lines.append(f"{i}. {title}")
    
    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": "\n".join(content_lines)
        }
    }
    
    return message


def build_dingtalk_favorites_message(articles: list) -> Dict:
    """构建钉钉收藏文章批量推送消息"""
    content_lines = [f"## 📚 收藏文章 ({len(articles)} 篇)\n"]
    
    for i, article in enumerate(articles, 1):
        title = article.get('title', '')
        link = article.get('link', '')
        
        if link:
            content_lines.append(f"{i}. [{title}]({link})")
        else:
            content_lines.append(f"{i}. {title}")
    
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"收藏文章 ({len(articles)} 篇)",
            "text": "\n".join(content_lines)
        }
    }
    
    return message


def build_generic_favorites_message(articles: list) -> Dict:
    """构建通用格式收藏文章批量推送消息"""
    content_lines = [f"**📚 收藏文章 ({len(articles)} 篇)**\n"]
    
    for i, article in enumerate(articles, 1):
        title = article.get('title', '')
        link = article.get('link', '')
        
        if link:
            content_lines.append(f"{i}. [{title}]({link})")
        else:
            content_lines.append(f"{i}. {title}")
    
    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"收藏文章 ({len(articles)} 篇)",
            "text": "\n".join(content_lines)
        }
    }
    
    return message

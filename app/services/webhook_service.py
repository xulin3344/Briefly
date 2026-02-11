from typing import Dict, List, Optional
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
    webhook_url: Optional[str] = None
) -> bool:
    """
    发送 Webhook 通知
    支持企业微信、钉钉等 Webhook 格式
    
    Args:
        title: 通知标题
        content: 通知内容
        url: 跳转链接（可选）
        webhook_url: Webhook URL，如果不提供则使用环境变量配置
        
    Returns:
        True 表示发送成功
    """
    # 检查 Webhook 是否启用
    if not settings.WEBHOOK_ENABLED and not webhook_url:
        logger.warning("Webhook 未启用")
        return False
    
    # 获取 Webhook URL
    target_url = webhook_url or settings.WEBHOOK_URL
    if not target_url:
        logger.error("Webhook URL 未配置")
        return False
    
    # 检测 Webhook 类型并构建消息格式
    message = build_webhook_message(title, content, url)
    
    try:
        # 发送 HTTP POST 请求
        with httpx.Client(timeout=30) as client:
            response = client.post(target_url, json=message)
            response.raise_for_status()
        
        logger.info(f"Webhook 通知发送成功: {title}")
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


def build_webhook_message(
    title: str,
    content: str,
    url: Optional[str] = None
) -> Dict:
    """
    构建 Webhook 消息格式
    自动检测 Webhook 类型并适配
    
    Args:
        title: 消息标题
        content: 消息内容
        url: 跳转链接
        
    Returns:
        适配各平台的消息格式
    """
    # 基础消息格式
    base_message = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"**{title}**\n\n{content}"
        }
    }
    
    # 如果有 URL，添加到消息中
    if url:
        base_message["markdown"]["text"] += f"\n\n[查看原文]({url})"
    
    return base_message


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
    测试 Webhook 连接
    
    Returns:
        测试结果字典
    """
    if not settings.WEBHOOK_ENABLED or not settings.WEBHOOK_URL:
        return {
            "success": False,
            "message": "Webhook 未配置"
        }
    
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

"""
API 认证模块

提供可选的 API 认证机制，保护 API 端点
"""
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import APIKeyHeader

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# API Key Header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthConfig:
    """认证配置"""
    
    # 不需要认证的路径（公开端点）
    PUBLIC_PATHS = {
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/index.html",
        "/config.html",
    }
    
    # 静态文件路径前缀（不需要认证）
    PUBLIC_PREFIXES = [
        "/static/",
    ]


def is_public_path(path: str) -> bool:
    """
    检查路径是否为公开路径
    
    Args:
        path: 请求路径
        
    Returns:
        是否为公开路径
    """
    if path in AuthConfig.PUBLIC_PATHS:
        return True
    
    for prefix in AuthConfig.PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    
    return False


async def verify_api_key(
    api_key: Optional[str] = Depends(api_key_header)
) -> bool:
    """
    验证 API Key
    
    如果认证未启用，直接返回 True
    
    Args:
        api_key: 请求头中的 API Key
        
    Returns:
        认证是否通过
        
    Raises:
        HTTPException: 认证失败时抛出 401 错误
    """
    # 如果认证未启用，直接通过
    if not settings.API_AUTH_ENABLED:
        return True
    
    # 检查 API Key 是否配置
    if not settings.API_AUTH_KEY:
        logger.warning("API 认证已启用但未配置 API_AUTH_KEY")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API authentication not properly configured"
        )
    
    # 验证 API Key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Please provide X-API-Key header."
        )
    
    # 使用常量时间比较防止时序攻击
    if not secrets.compare_digest(api_key, settings.API_AUTH_KEY):
        logger.warning(f"Invalid API Key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    return True


def generate_api_key() -> str:
    """
    生成安全的 API Key
    
    Returns:
        32 字节的十六进制 API Key
    """
    return secrets.token_hex(32)


class AuthMiddleware:
    """
    认证中间件
    
    可以作为 FastAPI 中间件或路由依赖使用
    """
    
    def __init__(self, app=None):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # 检查是否为公开路径
        path = scope.get("path", "")
        if is_public_path(path):
            await self.app(scope, receive, send)
            return
        
        # 如果认证未启用，直接通过
        if not settings.API_AUTH_ENABLED:
            await self.app(scope, receive, send)
            return
        
        # 从请求头获取 API Key
        headers = dict(scope.get("headers", []))
        api_key = headers.get(b"x-api-key", b"").decode("utf-8")
        
        # 验证 API Key
        if not api_key or not settings.API_AUTH_KEY:
            await self._send_error(send, 401, "Unauthorized: Missing or invalid API Key")
            return
        
        if not secrets.compare_digest(api_key, settings.API_AUTH_KEY):
            await self._send_error(send, 401, "Unauthorized: Invalid API Key")
            return
        
        await self.app(scope, receive, send)
    
    async def _send_error(self, send, status_code: int, message: str):
        """发送错误响应"""
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": f'{{"detail": "{message}"}}'.encode("utf-8"),
        })


# 用于路由依赖的快捷函数
async def require_auth(authenticated: bool = Depends(verify_api_key)):
    """
    路由认证依赖
    
    用法:
        @router.get("/protected", dependencies=[Depends(require_auth)])
        async def protected_route():
            ...
    """
    return authenticated

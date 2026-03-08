"""
全局异常处理器

提供统一的异常处理机制，确保 API 返回一致的错误格式
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from typing import Union

from app.core.response import ErrorResponse

logger = logging.getLogger(__name__)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    处理请求验证错误
    
    将 Pydantic 验证错误转换为友好的错误消息
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "code": error.get("type")
        })
    
    logger.warning(f"请求验证失败: {request.url} - {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "ValidationError",
            "message": "请求参数验证失败",
            "details": errors
        }
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """
    处理 HTTP 异常
    """
    logger.warning(f"HTTP 异常: {request.url} - {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.__class__.__name__,
            "message": str(exc.detail) if exc.detail else "请求处理失败"
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    处理未捕获的异常
    
    记录完整的异常信息，返回通用错误消息
    """
    logger.exception(f"未处理的异常: {request.url} - {exc.__class__.__name__}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "InternalServerError",
            "message": "服务器内部错误，请稍后重试"
        }
    )


def register_exception_handlers(app):
    """
    注册所有异常处理器到 FastAPI 应用
    
    Args:
        app: FastAPI 应用实例
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    # 注意：不要在生产环境注册通用异常处理器，可能会掩盖真正的错误
    # app.add_exception_handler(Exception, generic_exception_handler)

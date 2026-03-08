"""
统一响应模型和异常处理

提供标准化的 API 响应格式和全局异常处理器
"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    统一 API 响应模型
    
    所有 API 端点应该使用此模型包装返回数据
    """
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def ok(cls, data: T = None, message: str = None) -> "ApiResponse[T]":
        """创建成功响应"""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def fail(cls, error: str = None, message: str = None) -> "ApiResponse[T]":
        """创建失败响应"""
        return cls(success=False, error=error, message=message)


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应模型
    """
    items: List[T]
    total: int
    page: int
    page_size: int
    has_more: bool
    
    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    """错误详情"""
    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    message: Optional[str] = None
    details: Optional[List[ErrorDetail]] = None

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    应用配置管理
    使用 .env 文件加载环境变量，支持默认值和验证
    """
    # API Keys
    OPENAI_API_KEY: str = ""
    ZHIPUAI_API_KEY: str = ""
    ZHIPUAI_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    
    # Database - SQLite 数据库路径
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/briefly.db"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # RSS Fetcher
    FETCH_INTERVAL_MINUTES: int = 60
    REQUEST_TIMEOUT: int = 30
    MAX_RETRY_ATTEMPTS: int = 3  # RSS 抓取最大重试次数
    RETRY_MIN_WAIT: int = 2  # 重试最小等待时间（秒）
    RETRY_MAX_WAIT: int = 10  # 重试最大等待时间（秒）
    DESCRIPTION_MAX_LENGTH: int = 500  # 文章描述最大长度
    
    # Article Cache - 文章缓存设置
    ARTICLE_CACHE_DAYS: int = 3  # 只显示最近几天的文章
    FETCH_TODAY_ONLY: bool = True  # RSS 抓取时只获取当天的文章
    AUTO_CLEANUP_ENABLED: bool = True  # 是否启用自动清理旧文章
    CLEANUP_DAYS: int = 7  # 自动清理多少天前的文章
    
    # Auto Reset - 自动重置设置
    AUTO_RESET_ENABLED: bool = True  # 是否启用自动重置
    AUTO_RESET_HOUR: int = 4  # 每天几点重置（24小时制，默认凌晨4点）
    
    # AI Summary
    AI_MODEL: str = "glm-4"
    MAX_SUMMARY_LENGTH: int = 100
    
    # Webhook
    WEBHOOK_ENABLED: bool = False
    WEBHOOK_URL: str = ""
    
    # CORS - 允许的域名列表，多个域名用逗号分隔
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"
    
    # Security
    API_AUTH_ENABLED: bool = False
    API_AUTH_KEY: str = ""
    SECRET_KEY: str = "briefly-default-secret-key-change-in-production"
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    @field_validator('PORT')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """验证端口号范围"""
        if not 1 <= v <= 65535:
            raise ValueError('PORT must be between 1 and 65535')
        return v
    
    @field_validator('FETCH_INTERVAL_MINUTES')
    @classmethod
    def validate_fetch_interval(cls, v: int) -> int:
        """验证抓取间隔"""
        if v < 1:
            raise ValueError('FETCH_INTERVAL_MINUTES must be at least 1')
        return v
    
    @field_validator('REQUEST_TIMEOUT')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """验证请求超时"""
        if v < 5:
            raise ValueError('REQUEST_TIMEOUT must be at least 5 seconds')
        return v
    
    def validate_for_production(self) -> list[str]:
        """
        生产环境配置验证
        
        Returns:
            警告消息列表
        """
        warnings = []
        if self.DEBUG:
            warnings.append("DEBUG mode should be disabled in production")
        if not self.API_AUTH_ENABLED:
            warnings.append("API authentication is disabled")
        if "*" in self.ALLOWED_ORIGINS:
            warnings.append("CORS allows all origins - this is a security risk")
        if not self.DATABASE_URL.startswith("sqlite"):
            warnings.append(f"Database URL should be verified for production: {self.DATABASE_URL[:30]}...")
        return warnings


@lru_cache()  # 缓存配置，避免重复加载
def get_settings() -> Settings:
    """
    获取应用配置实例
    使用方法：from app.config import settings
    """
    return Settings()


# 全局配置实例
settings = get_settings()

# 启动时进行生产环境检查
if not settings.DEBUG:
    prod_warnings = settings.validate_for_production()
    for warning in prod_warnings:
        import warnings
        warnings.warn(f"[Briefly] {warning}")

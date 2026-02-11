import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    应用配置管理
    使用 .env 文件加载环境变量，支持默认值
    """
    # API Keys
    OPENAI_API_KEY: str = ""
    ZHIPUAI_API_KEY: str = ""
    
    # Database - SQLite 数据库路径
    # 默认使用本地相对路径，Docker 环境可通过环境变量覆盖
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/briefly.db"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # RSS Fetcher
    FETCH_INTERVAL_MINUTES: int = 60
    REQUEST_TIMEOUT: int = 30
    
    # AI Summary
    AI_MODEL: str = "glm-4"
    MAX_SUMMARY_LENGTH: int = 100
    
    # Webhook
    WEBHOOK_ENABLED: bool = False
    WEBHOOK_URL: str = ""
    
    # CORS - 允许的域名列表，多个域名用逗号分隔
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"
    
    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        env_file_encoding = "utf-8"


@lru_cache()  # 缓存配置，避免重复加载
def get_settings() -> Settings:
    """
    获取应用配置实例
    使用方法：from app.config import settings
    """
    return Settings()


# 全局配置实例
settings = get_settings()

# 智谱 AI 配置（硬编码）
ZHIPUAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

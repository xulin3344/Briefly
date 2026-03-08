from sqlalchemy import Column, Integer, String, Boolean, Text
from app.models.database import Base


class AIFilterConfig(Base):
    """AI 过滤配置模型"""
    __tablename__ = "ai_filter_config"

    id = Column(Integer, primary_key=True, index=True, default=1)
    enabled = Column(Boolean, default=False, comment="是否启用 AI 过滤")
    filter_prompt = Column(Text, nullable=True, comment="过滤提示词")
    auto_apply = Column(Boolean, default=True, comment="是否自动应用过滤")
    last_run = Column(String(50), nullable=True, comment="上次运行时间")

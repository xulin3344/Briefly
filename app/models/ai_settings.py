from sqlalchemy import Column, Integer, String, Boolean
from app.models.database import Base


class AISettings(Base):
    """AI 设置模型"""
    __tablename__ = "ai_settings"

    id = Column(Integer, primary_key=True, index=True, default=1)
    api_key = Column(String(500), nullable=True)
    base_url = Column(String(255), nullable=True)
    model = Column(String(100), default="glm-4")
    max_summary_length = Column(Integer, default=100)
    enabled = Column(Boolean, default=True)

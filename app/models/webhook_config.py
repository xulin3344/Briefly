from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.models.database import Base


class WebhookConfig(Base):
    """
    Webhook 配置模型
    存储 Webhook 推送的配置信息
    """
    __tablename__ = "webhook_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    url = Column(String(500), nullable=True)
    platform = Column(String(50), default="generic", nullable=False)  # wecom, dingtalk, feishu, feishu-card, feishu-flow, generic
    name = Column(String(100), nullable=True)  # Webhook 配置名称
    description = Column(Text, nullable=True)  # 描述信息
    
    # 定时推送配置
    schedule_enabled = Column(Boolean, default=False, nullable=False)  # 定时推送开关
    schedule_frequency = Column(String(20), default="hourly", nullable=False)  # hourly(每小时), daily(每天), weekly(每周), monthly(每月)
    schedule_time = Column(String(10), default="09:00", nullable=False)  # 推送时间，格式 HH:MM
    schedule_day_of_week = Column(Integer, default=1, nullable=False)  # 每周几 (1-7，周一为1)
    schedule_day_of_month = Column(Integer, default=1, nullable=False)  # 每月几号 (1-28)
    push_favorites = Column(Boolean, default=True, nullable=False)  # 是否推送收藏文章
    push_filtered = Column(Boolean, default=False, nullable=False)  # 是否推送过滤文章
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "enabled": self.enabled,
            "url": self.url,
            "platform": self.platform,
            "name": self.name,
            "description": self.description,
            "schedule_enabled": self.schedule_enabled,
            "schedule_frequency": self.schedule_frequency,
            "schedule_time": self.schedule_time,
            "schedule_day_of_week": self.schedule_day_of_week,
            "schedule_day_of_month": self.schedule_day_of_month,
            "push_favorites": self.push_favorites,
            "push_filtered": self.push_filtered,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

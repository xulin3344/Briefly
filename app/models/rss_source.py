from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.models.database import Base


class RSSSource(Base):
    """
    RSS 源数据模型
    存储用户添加的 RSS 订阅源信息
    """
    __tablename__ = "rss_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="RSS 源名称")
    url = Column(String(2048), nullable=False, unique=True, index=True, comment="RSS 订阅 URL")
    description = Column(String(500), nullable=True, comment="RSS 源描述")
    enabled = Column(Boolean, default=True, comment="是否启用抓取")
    last_fetched = Column(DateTime, nullable=True, comment="上次抓取时间")
    fetch_error_count = Column(Integer, default=0, comment="连续抓取失败次数")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    def __repr__(self):
        return f"<RSSSource(id={self.id}, name='{self.name}', url='{self.url}')>"

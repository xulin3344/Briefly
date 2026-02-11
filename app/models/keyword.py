from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.models.database import Base


class KeywordConfig(Base):
    """
    关键词配置数据模型
    存储用户设置的关键词过滤规则
    支持多关键词 OR 逻辑匹配
    """
    __tablename__ = "keyword_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True, comment="关键词（不区分大小写匹配）")
    enabled = Column(Boolean, default=True, comment="是否启用该关键词")
    match_count = Column(Integer, default=0, comment="匹配次数统计")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    def __repr__(self):
        return f"<KeywordConfig(id={self.id}, keyword='{self.keyword}', enabled={self.enabled})>"

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base


class Article(Base):
    """
    文章数据模型
    存储从 RSS 源抓取的文章信息
    """
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("rss_sources.id"), nullable=False, index=True, comment="所属 RSS 源 ID")
    
    # 文章基本信息
    guid = Column(String(2048), nullable=False, index=True, comment="文章唯一标识符（RSS 中的 guid）")
    title = Column(String(500), nullable=False, comment="文章标题")
    link = Column(String(2048), nullable=False, comment="文章原文链接")
    description = Column(Text, nullable=True, comment="文章摘要/简介")
    content = Column(Text, nullable=True, comment="文章全文内容")
    author = Column(String(255), nullable=True, comment="文章作者")
    published_at = Column(DateTime, nullable=True, index=True, comment="文章发布时间")
    
    # 处理状态
    is_filtered = Column(Boolean, default=False, comment="是否被关键词过滤")
    is_ai_filtered = Column(Boolean, default=False, comment="是否被 AI 过滤")
    has_summary = Column(Boolean, default=False, comment="是否已生成 AI 总结")
    summary = Column(Text, nullable=True, comment="AI 生成的摘要（100 字以内）")
    is_read = Column(Boolean, default=False, comment="是否已阅读")
    is_favorite = Column(Boolean, default=False, comment="是否收藏")
    
    # 元信息
    fetched_at = Column(DateTime, default=datetime.utcnow, comment="抓取时间")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系定义
    source = relationship("RSSSource", back_populates="articles")
    
    # 复合索引：优化常用查询性能
    __table_args__ = (
        Index('idx_source_published', 'source_id', 'published_at'),  # 按源和时间排序
        Index('idx_filtered_read', 'is_filtered', 'is_read'),  # 过滤和已读状态
        Index('idx_source_filtered', 'source_id', 'is_filtered'),  # 按源和过滤状态
        {"sqlite_autoincrement": True},
    )
    
    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:50]}...')>"

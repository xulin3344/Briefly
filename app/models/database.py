from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# 使用配置文件中的 DATABASE_URL，支持本地开发和 Docker 环境
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG
)

AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    from app.models import article, rss_source, keyword, ai_settings, webhook_config
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

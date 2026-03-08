from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.config import settings

database_url = make_url(settings.DATABASE_URL)
engine_kwargs = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}

if database_url.drivername.startswith("sqlite"):
    if database_url.database in (None, "", ":memory:"):
        engine_kwargs["poolclass"] = StaticPool
    else:
        engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 3600,
            "pool_timeout": 30,
        }
    )

async_engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    expire_on_commit=False,
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
    from app.models import (
        ai_filter_config,
        ai_settings,
        article,
        keyword,
        rss_source,
        webhook_config,
    )

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

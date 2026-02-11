"""
测试配置文件
提供测试用的 fixtures 和数据库配置
"""
import pytest
import os
import asyncio
from typing import Generator

# 设置测试环境变量（必须在导入 app 之前）
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_briefly.db"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def client():
    """测试客户端 - 使用真实的测试数据库"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models.database import async_engine, Base
    import asyncio
    
    # 创建测试数据库表
    async def create_tables():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    # 运行创建表
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(create_tables())
    
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    
    # 清理
    async def drop_tables():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    loop.run_until_complete(drop_tables())
    loop.close()


@pytest.fixture
def sample_rss_source():
    """示例 RSS 源数据"""
    return {
        "name": "Test RSS Source",
        "url": "http://example.com/rss.xml",
        "description": "A test RSS source"
    }


@pytest.fixture
def sample_article():
    """示例文章数据"""
    return {
        "title": "Test Article",
        "link": "http://example.com/article/1",
        "description": "This is a test article",
        "content": "Full content of the test article",
        "author": "Test Author"
    }

"""
Briefly RSS 聚合器 - API 测试
"""
import pytest
from fastapi.testclient import TestClient
import os
import asyncio
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境
os.environ["TESTING"] = "1"


@pytest.fixture(scope="module")
def client():
    """测试客户端"""
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "database" in data

    def test_health_check_reports_database_failure(self, client):
        with patch(
            "app.routes.system.AsyncSession.execute",
            new=AsyncMock(side_effect=RuntimeError("db down")),
        ):
            response = client.get("/api/health")

        assert response.status_code == 503
        assert response.json()["message"]


class TestStatusEndpoint:
    def test_get_status(self, client):
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        # 检查返回的状态数据
        assert "database" in data
        assert "scheduler" in data
        assert "ai_configured" in data

    def test_get_status_uses_database_ai_settings(self, client):
        from app.models import AISettings, AsyncSessionLocal

        async def seed_ai_settings():
            async with AsyncSessionLocal() as db:
                settings_row = await db.get(AISettings, 1)
                if settings_row is None:
                    settings_row = AISettings(id=1)
                    db.add(settings_row)

                # Plaintext keeps the test independent from environment-specific keys.
                settings_row.api_key = "plain-test-key"
                await db.commit()

        asyncio.run(seed_ai_settings())

        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ai_configured"] is True


class TestRSSSourcesAPI:
    def test_list_rss_sources(self, client):
        response = client.get("/api/sources")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_rss_source_not_found(self, client):
        response = client.get("/api/sources/9999")
        assert response.status_code == 404

    def test_create_rss_source_validation(self, client):
        response = client.post("/api/sources", json={})
        assert response.status_code == 422


class TestArticlesAPI:
    def test_list_articles(self, client):
        response = client.get("/api/articles")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "total" in data

    def test_list_articles_with_pagination(self, client):
        response = client.get("/api/articles?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data


class TestKeywordsAPI:
    def test_list_keywords(self, client):
        response = client.get("/api/keywords")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSystemAPI:
    def test_get_ai_config(self, client):
        """测试获取 AI 配置"""
        response = client.get("/api/ai/config")
        assert response.status_code == 200
        data = response.json()
        # 检查 AI 配置返回
        assert "model" in data or "enabled" in data or "has_api_key" in data

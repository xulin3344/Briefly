import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data


class TestStatusEndpoint:
    def test_get_status(self, client):
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data


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
        assert "items" in data
        assert "total" in data

    def test_list_articles_with_pagination(self, client):
        response = client.get("/api/articles?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
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
    def test_get_config(self, client):
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "settings" in data

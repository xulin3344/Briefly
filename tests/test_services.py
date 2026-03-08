"""
Briefly RSS 聚合器 - 服务层测试

测试核心服务功能，包括安全模块、认证模块等
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境
os.environ["TESTING"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"


class TestSecurityModule:
    """安全模块测试"""
    
    def test_encrypt_decrypt_api_key(self):
        """测试 API Key 加密解密"""
        from app.core.security import encrypt_api_key, decrypt_api_key
        
        original_key = "sk-test-1234567890abcdef"
        
        # 加密
        encrypted = encrypt_api_key(original_key)
        
        # 验证加密后的格式
        assert encrypted.startswith("enc_v2:")
        assert encrypted != original_key
        
        # 解密
        decrypted = decrypt_api_key(encrypted)
        
        # 验证解密后与原始值相同
        assert decrypted == original_key
    
    def test_encrypt_empty_key(self):
        """测试空 API Key 加密"""
        from app.core.security import encrypt_api_key, decrypt_api_key
        
        assert encrypt_api_key("") == ""
        assert decrypt_api_key("") == ""
    
    def test_decrypt_unencrypted_key(self):
        """测试解密未加密的 Key（向后兼容）"""
        from app.core.security import decrypt_api_key
        
        # 没有 "enc:" 前缀的值应该原样返回
        unencrypted = "plain-api-key"
        assert decrypt_api_key(unencrypted) == unencrypted
    
    def test_mask_api_key(self):
        """测试 API Key 遮蔽"""
        from app.core.security import mask_api_key
        
        key = "sk-1234567890abcdefghijklmnop"
        
        masked = mask_api_key(key, visible_chars=4)
        
        assert masked.startswith("sk-1")
        assert masked.endswith("mnop")
        assert "..." in masked
    
    def test_mask_short_key(self):
        """测试短 API Key 遮蔽"""
        from app.core.security import mask_api_key
        
        short_key = "abc"
        masked = mask_api_key(short_key)
        
        # 短 key 应该全部遮蔽
        assert "*" in masked or masked == "***"
    
    def test_is_encrypted(self):
        """测试加密检测"""
        from app.core.security import is_encrypted
        
        assert is_encrypted("enc:somedata") is True
        assert is_encrypted("plainkey") is False
        assert is_encrypted("") is False


class TestAuthModule:
    """认证模块测试"""
    
    def test_is_public_path(self):
        """测试公开路径检测"""
        from app.core.auth import is_public_path
        
        # 公开路径
        assert is_public_path("/") is True
        assert is_public_path("/docs") is True
        assert is_public_path("/redoc") is True
        assert is_public_path("/static/css/style.css") is True
        
        # 需要认证的路径
        assert is_public_path("/api/articles") is False
        assert is_public_path("/api/sources") is False
    
    def test_generate_api_key(self):
        """测试 API Key 生成"""
        from app.core.auth import generate_api_key
        
        key1 = generate_api_key()
        key2 = generate_api_key()
        
        # 每个 key 应该唯一
        assert key1 != key2
        
        # key 应该是 64 个十六进制字符 (32 字节)
        assert len(key1) == 64
        assert all(c in '0123456789abcdef' for c in key1)
    
    @pytest.mark.asyncio
    async def test_verify_api_key_disabled(self):
        """测试认证禁用时的验证"""
        from app.core.auth import verify_api_key
        from app.config import settings
        
        # 当认证禁用时，应该直接通过
        with patch.object(settings, 'API_AUTH_ENABLED', False):
            result = await verify_api_key(None)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_verify_api_key_missing(self):
        """测试缺少 API Key 时的验证"""
        from app.core.auth import verify_api_key
        from app.config import settings
        from fastapi import HTTPException
        
        with patch.object(settings, 'API_AUTH_ENABLED', True), \
             patch.object(settings, 'API_AUTH_KEY', 'test-key'):
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(None)
            
            assert exc_info.value.status_code == 401


class TestResponseModels:
    """响应模型测试"""
    
    def test_api_response_ok(self):
        """测试成功响应模型"""
        from app.core.response import ApiResponse
        
        response = ApiResponse.ok(data={"key": "value"}, message="Success")
        
        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.message == "Success"
        assert response.error is None
    
    def test_api_response_fail(self):
        """测试失败响应模型"""
        from app.core.response import ApiResponse
        
        response = ApiResponse.fail(error="ValidationError", message="Invalid input")
        
        assert response.success is False
        assert response.error == "ValidationError"
        assert response.message == "Invalid input"
        assert response.data is None
    
    def test_paginated_response(self):
        """测试分页响应模型"""
        from app.core.response import PaginatedResponse
        
        response = PaginatedResponse(
            items=[1, 2, 3],
            total=100,
            page=1,
            page_size=20,
            has_more=True
        )
        
        assert response.items == [1, 2, 3]
        assert response.total == 100
        assert response.page == 1
        assert response.has_more is True


class TestExceptions:
    """异常处理器测试"""
    
    def test_error_response_model(self):
        """测试错误响应模型"""
        from app.core.response import ErrorResponse, ErrorDetail
        
        response = ErrorResponse(
            error="ValidationError",
            message="Invalid input",
            details=[
                ErrorDetail(field="name", message="Name is required", code="required")
            ]
        )
        
        assert response.success is False
        assert response.error == "ValidationError"
        assert len(response.details) == 1
        assert response.details[0].field == "name"


class TestRSSOptimizations:
    """RSS related regression tests."""

    @pytest.mark.asyncio
    async def test_save_articles_skips_existing_and_incoming_duplicates(self):
        from app.models import Article, AsyncSessionLocal, RSSSource
        from app.services.rss_service import save_articles

        async with AsyncSessionLocal() as db:
            source = RSSSource(
                name="Test Feed",
                url=f"https://example.com/{uuid4()}/feed",
            )
            db.add(source)
            await db.commit()
            await db.refresh(source)

            db.add(
                Article(
                    source_id=source.id,
                    guid="existing-guid",
                    title="Existing",
                    link="https://example.com/existing",
                    published_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()

            saved_count = await save_articles(
                db,
                source.id,
                [
                    {
                        "guid": "existing-guid",
                        "title": "Duplicate in DB",
                        "link": "https://example.com/existing",
                        "published_at": datetime.now(timezone.utc),
                    },
                    {
                        "guid": "new-guid",
                        "title": "New article",
                        "link": "https://example.com/new",
                        "published_at": datetime.now(timezone.utc),
                    },
                    {
                        "guid": "new-guid",
                        "title": "Duplicate in batch",
                        "link": "https://example.com/new-2",
                        "published_at": datetime.now(timezone.utc),
                    },
                ],
            )

            assert saved_count == 1

            result = await db.execute(
                Article.__table__.select().where(Article.source_id == source.id)
            )
            assert len(result.fetchall()) == 2

    @pytest.mark.asyncio
    async def test_fetch_source_awaits_async_feed_fetch(self):
        from app.models import AsyncSessionLocal, RSSSource
        from app.routes.sources import fetch_source

        async with AsyncSessionLocal() as db:
            source = RSSSource(
                name="Test Feed",
                url=f"https://example.com/{uuid4()}/fetch",
            )
            db.add(source)
            await db.commit()
            await db.refresh(source)

            with patch(
                "app.routes.sources.rss_service.fetch_rss_feed",
                new=AsyncMock(return_value=[{"guid": "g1", "title": "A", "link": "https://example.com/a"}]),
            ) as fetch_mock, patch(
                "app.routes.sources.rss_service.save_articles",
                new=AsyncMock(return_value=1),
            ) as save_mock:
                response = await fetch_source(source.id, db)

            fetch_mock.assert_awaited_once()
            save_mock.assert_awaited_once()
            assert response["success"] is True

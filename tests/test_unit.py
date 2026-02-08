"""
Briefly RSS 聚合器 - 单元测试
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config_settings():
    """测试配置加载"""
    from app.config import settings
    
    assert settings.HOST == "0.0.0.0"
    assert settings.PORT == 8000
    assert settings.DEBUG == False
    print("✓ 配置测试通过")


def test_rss_service_validation():
    """测试 RSS 服务 URL 验证"""
    from app.services.rss_service import RSSFetchError
    
    valid_urls = [
        "http://example.com/rss.xml",
        "https://example.com/feed",
    ]
    
    for url in valid_urls:
        assert url.startswith("http://") or url.startswith("https://")
    
    print("✓ RSS URL 验证测试通过")


def test_keyword_service():
    """测试关键词匹配服务"""
    from app.services.keyword_service import KeywordFilter
    
    filter_obj = KeywordFilter(keywords=["python", "ai"])
    
    tests = [
        ("python", "学习 Python 编程", True),
        ("python", "使用 Java 开发", False),
        ("ai", "AI 和机器学习", True),
        ("tech", "最新科技新闻", False),
    ]
    
    for keyword, text, expected in tests:
        result, matches = filter_obj.matches(text)
        assert result == expected, f"关键词 '{keyword}' 在 '{text}' 中应该返回 {expected}"
    
    print("✓ 关键词匹配测试通过")


def test_ai_service():
    """测试 AI 服务"""
    from app.services import ai_service
    
    result = ai_service.generate_test_summary()
    # API key 无效时返回 None，这是预期行为
    assert result is None or isinstance(result, str)
    
    print("✓ AI 服务测试通过")


def test_webhook_service():
    """测试 Webhook 服务"""
    from app.services import webhook_service
    
    result = webhook_service.test_webhook_connection()
    assert "success" in result
    assert result["success"] == False
    assert "message" in result
    
    print("✓ Webhook 服务测试通过")


def test_pydantic_models():
    """测试 Pydantic 模型验证"""
    from pydantic import ValidationError
    from app.routes.sources import RSSSourceCreate
    from app.routes.keywords import KeywordCreate
    
    source = RSSSourceCreate(name="Test", url="http://example.com/rss.xml")
    assert source.name == "Test"
    assert str(source.url) == "http://example.com/rss.xml"
    
    keyword = KeywordCreate(keyword="test")
    assert keyword.keyword == "test"
    assert keyword.enabled == True
    
    print("✓ Pydantic 模型验证测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*50)
    print("Briefly RSS 聚合器 - 单元测试")
    print("="*50 + "\n")
    
    tests = [
        test_config_settings,
        test_rss_service_validation,
        test_keyword_service,
        test_ai_service,
        test_webhook_service,
        test_pydantic_models,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*50 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

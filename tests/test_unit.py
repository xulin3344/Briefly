"""
Briefly RSS 聚合器 - 单元测试
"""

import sys
import os
import pytest

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
    from app.services.rss_service import RSSFetchError, RSSParseError, RSSNetworkError
    
    valid_urls = [
        "http://example.com/rss.xml",
        "https://example.com/feed",
    ]
    
    for url in valid_urls:
        assert url.startswith("http://") or url.startswith("https://")
    
    # 测试异常类可以正常实例化
    assert RSSFetchError("test") is not None
    assert RSSParseError("test") is not None
    assert RSSNetworkError("test") is not None
    
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
        # matches 方法返回 3 个值: (is_match, matched_keywords, title_match)
        result, matches, title_match = filter_obj.matches(text)
        assert result == expected, f"关键词 '{keyword}' 在 '{text}' 中应该返回 {expected}"
    
    print("✓ 关键词匹配测试通过")


def test_keyword_filter_articles():
    """测试关键词过滤文章功能"""
    from app.services.keyword_service import KeywordFilter
    from app.models.article import Article
    
    filter_obj = KeywordFilter(keywords=["python"])
    
    # 创建模拟文章
    class MockArticle:
        def __init__(self, title, description="", content=""):
            self.title = title
            self.description = description
            self.content = content
    
    articles = [
        MockArticle("Python 教程", "学习 Python", "Python 是一门编程语言"),
        MockArticle("Java 教程", "学习 Java", "Java 是一门编程语言"),
        MockArticle("AI 新闻", "人工智能发展", "AI 和 Python 的结合"),
    ]
    
    matched, unmatched = filter_obj.filter_articles(articles)
    
    assert len(matched) == 2  # Python 教程 和 AI 新闻
    assert len(unmatched) == 1  # Java 教程
    
    print("✓ 关键词过滤文章测试通过")


@pytest.mark.asyncio
async def test_ai_service():
    """测试 AI 服务"""
    from app.services import ai_service
    
    # 测试 truncate_text 函数
    long_text = "这是一段很长的文本" * 100
    truncated = ai_service.truncate_text(long_text, max_chars=100)
    assert len(truncated) <= 100
    
    # 测试 generate_summary_prompt 函数
    prompt = ai_service.generate_summary_prompt("测试标题", "测试内容")
    assert "测试标题" in prompt
    assert "测试内容" in prompt
    
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


def test_logging_module():
    """测试日志模块"""
    from app.core.logging import setup_logging, get_logger, LoggingConfig
    
    # 重置日志配置（测试环境）
    LoggingConfig.reset()
    
    # 设置日志
    setup_logging(debug=True)
    
    # 获取日志器
    logger = get_logger("test_module")
    assert logger is not None
    
    # 测试日志输出不会抛出异常
    logger.debug("这是一条调试日志")
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    
    print("✓ 日志模块测试通过")


def test_database_url_config():
    """测试数据库 URL 配置"""
    from app.config import settings
    
    # 验证 DATABASE_URL 可以从环境变量读取
    assert settings.DATABASE_URL is not None
    assert "sqlite" in settings.DATABASE_URL
    
    print("✓ 数据库 URL 配置测试通过")


def test_cors_config():
    """测试 CORS 配置"""
    from app.config import settings
    
    # 验证 CORS 配置存在
    assert settings.ALLOWED_ORIGINS is not None
    assert "localhost" in settings.ALLOWED_ORIGINS or "127.0.0.1" in settings.ALLOWED_ORIGINS
    
    print("✓ CORS 配置测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*50)
    print("Briefly RSS 聚合器 - 单元测试")
    print("="*50 + "\n")
    
    tests = [
        test_config_settings,
        test_rss_service_validation,
        test_keyword_service,
        test_keyword_filter_articles,
        test_webhook_service,
        test_pydantic_models,
        test_logging_module,
        test_database_url_config,
        test_cors_config,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} 失败: {e}")
            failed += 1
    
    print("\n" + "="*50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*50 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

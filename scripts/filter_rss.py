#!/usr/bin/env python3
"""
关键词 RSS 筛选脚本
功能：解析 RSS 源，按关键词筛选文章
- 包含词：必须包含 '自动驾驶' 或 '无人机'
- 排除词：不能包含 '代理' 或 '加盟'
- 输出：打印匹配成功的文章标题和链接（去重）
"""

import feedparser
from urllib.parse import urlparse
import hashlib
from typing import Set, Tuple


class KeywordFilter:
    def __init__(self, include_keywords: list, exclude_keywords: list):
        self.include_keywords = [kw.lower() for kw in include_keywords]
        self.exclude_keywords = [kw.lower() for kw in exclude_keywords]

    def matches(self, title: str, summary: str) -> Tuple[bool, str]:
        """
        检查文章是否匹配筛选条件
        返回: (是否匹配, 匹配的关键词)
        """
        text = f"{title} {summary}".lower()

        # 检查排除词
        for exclude_kw in self.exclude_keywords:
            if exclude_kw in text:
                return False, exclude_kw

        # 检查包含词（必须包含至少一个）
        for include_kw in self.include_keywords:
            if include_kw in text:
                return True, include_kw

        return False, ""

    def should_include(self, title: str, summary: str) -> bool:
        """判断文章是否应该包含"""
        match, _ = self.matches(title, summary)
        return match


def parse_rss(url: str) -> list:
    """解析 RSS 源"""
    print(f"\n{'='*60}")
    print(f"正在解析: {url}")
    print(f"{'='*60}")

    feed = feedparser.parse(url)

    if feed.bozo:
        print(f"⚠️  RSS 解析警告: {feed.bozo_exception}")

    if not hasattr(feed, 'entries') or len(feed.entries) == 0:
        print(f"❌ 未能获取到文章")
        return []

    print(f"✅ 成功获取 {len(feed.entries)} 篇文章\n")
    return feed.entries


def extract_article_info(entry) -> Tuple[str, str, str]:
    """提取文章信息"""
    title = entry.get('title', '无标题')

    summary = ''
    if hasattr(entry, 'summary'):
        summary = entry.summary
    elif hasattr(entry, 'description'):
        summary = entry.description

    link = ''
    if hasattr(entry, 'link'):
        link = entry.link
        if isinstance(link, list):
            link = link[0]

    return title, summary, link


def get_article_hash(title: str, link: str) -> str:
    """生成文章唯一标识（用于去重）"""
    content = f"{title.lower().strip()}|{link.lower().strip()}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]


def filter_rss(rss_urls: list, include_keywords: list, exclude_keywords: list) -> list:
    """
    筛选 RSS 文章

    Args:
        rss_urls: RSS 源列表
        include_keywords: 必须包含的关键词列表
        exclude_keywords: 不能包含的关键词列表

    Returns:
        匹配的文章列表
    """
    filter_obj = KeywordFilter(include_keywords, exclude_keywords)
    seen_hashes: Set[str] = set()
    matched_articles = []

    print(f"\n{'🔍 筛选配置'}")
    print(f"包含词: {include_keywords}")
    print(f"排除词: {exclude_keywords}")
    print(f"{'─'*40}")

    for rss_url in rss_urls:
        entries = parse_rss(rss_url)

        for entry in entries:
            title, summary, link = extract_article_info(entry)

            if not link:
                continue

            article_hash = get_article_hash(title, link)
            if article_hash in seen_hashes:
                continue

            if filter_obj.should_include(title, summary):
                seen_hashes.add(article_hash)
                matched_articles.append({
                    'title': title,
                    'link': link,
                    'source': urlparse(rss_url).netloc
                })

    return matched_articles


def print_results(articles: list):
    """打印筛选结果"""
    print(f"\n{'='*60}")
    print(f"📊 筛选结果: 共找到 {len(articles)} 篇匹配的文章")
    print(f"{'='*60}\n")

    if not articles:
        print("未找到匹配的文章")
        return

    for i, article in enumerate(articles, 1):
        print(f"{i:3}. {article['title'][:50]}...")
        print(f"    🔗 {article['link'][:80]}")
        print(f"    📰 来源: {article['source']}")
        print()


def main():
    # RSS 源配置
    RSS_SOURCES = [
        "https://36kr.com/feed/",
        "https://www.sspai.com/feed",
        "https://www.techcrunch.com/feed/",
        # 在这里添加更多 RSS 源
    ]

    # 包含词（必须包含）
    INCLUDE_KEYWORDS = [
        "自动驾驶",
        "无人机",
    ]

    # 排除词（不能包含）
    EXCLUDE_KEYWORDS = [
        "代理",
        "加盟",
    ]

    # 筛选并打印结果
    articles = filter_rss(RSS_SOURCES, INCLUDE_KEYWORDS, EXCLUDE_KEYWORDS)
    print_results(articles)

    # 保存结果到文件（可选）
    if articles:
        with open('filtered_articles.txt', 'w', encoding='utf-8') as f:
            for article in articles:
                f.write(f"{article['title']}\n")
                f.write(f"{article['link']}\n")
                f.write(f"{'─'*40}\n")
        print(f"\n💾 结果已保存到: filtered_articles.txt")


if __name__ == "__main__":
    main()

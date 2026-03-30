"""RSS/Atom 订阅源模块：解析 Feed 获取资讯内容，作为网页爬取的补充"""

import asyncio
import logging
import re

import feedparser
import httpx

from src.crawler import CrawlResult

logger = logging.getLogger(__name__)

# HTML 标签清理正则
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """移除 HTML 标签，保留纯文本"""
    return _HTML_TAG_RE.sub("", text).strip()


def _entries_to_markdown(entries: list, max_entries: int = 20) -> str:
    """将 Feed 条目转换为 Markdown，供 LLM 提取摘要

    格式与网页爬取结果类似，确保下游 LLM 提取逻辑无需修改。
    """
    lines: list[str] = []
    for entry in entries[:max_entries]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        published = getattr(entry, "published", "")

        # 优先 summary → description → content
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        if not summary:
            content_list = getattr(entry, "content", None)
            if content_list and isinstance(content_list, list):
                summary = content_list[0].get("value", "")
        summary = _strip_html(summary)

        if not title:
            continue

        lines.append(f"## {title}")
        if link:
            lines.append(f"Link: {link}")
        if published:
            lines.append(f"Published: {published}")
        if summary:
            # 截断过长摘要，避免单条占用过多 token
            if len(summary) > 500:
                summary = summary[:500] + "..."
            lines.append(summary)
        lines.append("")

    return "\n".join(lines)


async def fetch_feed(
    source: dict,
    timeout: int = 30,
    max_entries: int = 20,
    proxy: str | None = None,
) -> CrawlResult:
    """获取并解析单个 RSS/Atom Feed

    Args:
        source: 资讯源配置（需包含 name, url, category；可选 feed_url）
        timeout: HTTP 请求超时（秒）
        max_entries: 每个 Feed 最大条目数
        proxy: HTTP 代理地址
    """
    name = source["name"]
    category = source.get("category", "")
    url = source["url"]
    feed_url = source.get("feed_url", url)

    try:
        async with httpx.AsyncClient(
            proxy=proxy, timeout=timeout, follow_redirects=True,
        ) as client:
            resp = await client.get(feed_url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; LarkBrief/1.0)",
                "Accept": (
                    "application/rss+xml, application/atom+xml, "
                    "application/xml, text/xml, */*"
                ),
            })
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)

        if feed.bozo and not feed.entries:
            error = str(getattr(feed, "bozo_exception", "Feed 解析失败"))
            logger.warning("❌ Feed 解析失败: %s — %s", name, error)
            return CrawlResult(
                source_name=name, category=category,
                url=url, markdown="", success=False, error=error,
            )

        if not feed.entries:
            logger.warning("❌ Feed 无条目: %s", name)
            return CrawlResult(
                source_name=name, category=category,
                url=url, markdown="", success=False, error="Feed 无条目",
            )

        markdown = _entries_to_markdown(feed.entries, max_entries)
        logger.info(
            "✅ Feed 成功: %s (%d 条, %d 字符)",
            name, min(len(feed.entries), max_entries), len(markdown),
        )
        return CrawlResult(
            source_name=name, category=category,
            url=url, markdown=markdown, success=True,
        )

    except httpx.HTTPStatusError as e:
        error = f"HTTP {e.response.status_code}"
        logger.warning("❌ Feed 请求失败: %s — %s", name, error)
        return CrawlResult(
            source_name=name, category=category,
            url=url, markdown="", success=False, error=error,
        )
    except Exception as e:
        logger.warning("❌ Feed 异常: %s — %s", name, e)
        return CrawlResult(
            source_name=name, category=category,
            url=url, markdown="", success=False, error=str(e),
        )


async def fetch_feeds(
    sources: list[dict],
    timeout: int = 30,
    max_entries: int = 20,
    proxy: str | None = None,
) -> list[CrawlResult]:
    """并发获取多个 RSS/Atom Feed

    Args:
        sources: RSS 类型的资讯源配置列表
        timeout: HTTP 请求超时（秒）
        max_entries: 每个 Feed 最大条目数
        proxy: HTTP 代理地址
    """
    if not sources:
        return []

    logger.info(
        "开始获取 %d 个 RSS Feed: %s",
        len(sources), [s["name"] for s in sources],
    )

    tasks = [
        fetch_feed(s, timeout=timeout, max_entries=max_entries, proxy=proxy)
        for s in sources
    ]
    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r.success)
    logger.info("Feed 获取完成: %d/%d 成功", success_count, len(results))
    return list(results)

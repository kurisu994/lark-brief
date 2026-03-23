"""爬取模块：调用 crawl4ai 并发爬取资讯源，使用内容过滤去噪"""

import logging
from dataclasses import dataclass

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """单个资讯源的爬取结果"""
    source_name: str
    category: str
    url: str
    markdown: str
    success: bool
    error: str | None = None


async def crawl_sources(
    sources: list[dict],
    headless: bool = True,
    filter_threshold: float = 0.45,
) -> list[CrawlResult]:
    """并发爬取所有启用的资讯源，返回爬取结果列表

    Args:
        sources: 资讯源配置列表（来自 sources.yaml）
        headless: 是否使用无头浏览器模式
        filter_threshold: PruningContentFilter 去噪阈值
    """
    # 过滤出启用的源
    enabled = [s for s in sources if s.get("enabled", True)]
    if not enabled:
        logger.warning("没有启用的资讯源")
        return []

    urls = [s["url"] for s in enabled]
    logger.info("开始爬取 %d 个资讯源: %s", len(urls), [s["name"] for s in enabled])

    browser_config = BrowserConfig(headless=headless)
    crawler_config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=filter_threshold)
        )
    )

    results: list[CrawlResult] = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        raw_results = await crawler.arun_many(
            urls=urls,
            config=crawler_config,
        )

        for source, raw in zip(enabled, raw_results):
            if raw.success and raw.markdown_v2:
                # 优先使用过滤后的 fit_markdown，否则回退到原始 markdown
                content = raw.markdown_v2.fit_markdown or raw.markdown_v2.raw_markdown or ""
                results.append(CrawlResult(
                    source_name=source["name"],
                    category=source.get("category", ""),
                    url=source["url"],
                    markdown=content,
                    success=True,
                ))
                logger.info("✅ 爬取成功: %s (%d 字符)", source["name"], len(content))
            else:
                error_msg = raw.error_message if hasattr(raw, "error_message") else "未知错误"
                results.append(CrawlResult(
                    source_name=source["name"],
                    category=source.get("category", ""),
                    url=source["url"],
                    markdown="",
                    success=False,
                    error=error_msg,
                ))
                logger.warning("❌ 爬取失败: %s — %s", source["name"], error_msg)

    success_count = sum(1 for r in results if r.success)
    logger.info("爬取完成: %d/%d 成功", success_count, len(results))
    return results

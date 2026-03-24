"""爬取模块：调用 crawl4ai 并发爬取资讯源，使用内容过滤去噪"""

import logging
from dataclasses import dataclass

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

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

        # 建立 URL → 爬取结果 的映射（arun_many 返回顺序可能与输入不一致）
        result_map = {r.url: r for r in raw_results}

        for source in enabled:
            url = source["url"]
            raw = result_map.get(url)
            if raw is None:
                results.append(
                    CrawlResult(
                        source_name=source["name"],
                        category=source.get("category", ""),
                        url=url,
                        markdown="",
                        success=False,
                        error="未收到爬取结果",
                    )
                )
                logger.warning("❌ 爬取失败: %s — 未收到爬取结果", source["name"])
                continue
            try:
                if raw.success and raw.markdown:
                    # markdown 返回 MarkdownGenerationResult，含 fit_markdown / raw_markdown
                    md_result = raw.markdown
                    content = md_result.fit_markdown or md_result.raw_markdown or ""
                    if content:
                        results.append(
                            CrawlResult(
                                source_name=source["name"],
                                category=source.get("category", ""),
                                url=source["url"],
                                markdown=content,
                                success=True,
                            )
                        )
                        logger.info("✅ 爬取成功: %s (%d 字符)", source["name"], len(content))
                        continue
                # 爬取失败或内容为空
                error_msg = getattr(raw, "error_message", None) or "内容为空"
                results.append(
                    CrawlResult(
                        source_name=source["name"],
                        category=source.get("category", ""),
                        url=source["url"],
                        markdown="",
                        success=False,
                        error=error_msg,
                    )
                )
                logger.warning("❌ 爬取失败: %s — %s", source["name"], error_msg)
            except Exception as e:
                results.append(
                    CrawlResult(
                        source_name=source["name"],
                        category=source.get("category", ""),
                        url=source["url"],
                        markdown="",
                        success=False,
                        error=str(e),
                    )
                )
                logger.warning("❌ 爬取异常: %s — %s", source["name"], e)

    success_count = sum(1 for r in results if r.success)
    logger.info("爬取完成: %d/%d 成功", success_count, len(results))
    return results

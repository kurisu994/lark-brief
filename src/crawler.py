"""爬取模块：调用 crawl4ai 并发爬取资讯源，使用内容过滤去噪"""

from dataclasses import dataclass


@dataclass
class CrawlResult:
    """单个资讯源的爬取结果"""
    source_name: str
    category: str
    url: str
    markdown: str
    success: bool
    error: str | None = None


async def crawl_sources(sources: list[dict]) -> list[CrawlResult]:
    """并发爬取所有启用的资讯源，返回爬取结果列表"""
    # TODO: 实现爬取逻辑
    raise NotImplementedError

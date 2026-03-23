"""总结模块：调用火山引擎 LLM 提取新闻摘要，跨源去重排序"""

from dataclasses import dataclass


@dataclass
class NewsItem:
    """单条新闻"""
    summary: str
    url: str
    importance: int


async def extract_news(source_name: str, category: str, markdown: str) -> list[NewsItem]:
    """从单个资讯源的内容中提取新闻摘要"""
    # TODO: 实现 LLM 提取逻辑
    raise NotImplementedError


async def merge_and_rank(all_news: list[NewsItem], max_items: int = 15, min_items: int = 10) -> list[NewsItem]:
    """跨源去重、按重要性排序，选取指定数量的新闻"""
    # TODO: 实现去重排序逻辑
    raise NotImplementedError

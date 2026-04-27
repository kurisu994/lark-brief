import pytest

from src import summarizer
from src.crawler import select_sources
from src.summarizer import NewsItem


def test_select_sources_respects_category_weights() -> None:
    sources = [
        {"name": "安全源", "url": "https://security.example", "category": "网络安全"},
        {"name": "国内源", "url": "https://domestic.example", "category": "国内时事"},
        {"name": "国际源", "url": "https://world.example", "category": "国际时事"},
    ]

    selected = select_sources(
        sources,
        select_count=2,
        category_weights={
            "网络安全": 0.0,
            "国内时事": 10.0,
            "国际时事": 10.0,
        },
    )

    assert {source["category"] for source in selected} == {"国内时事", "国际时事"}


@pytest.mark.asyncio
async def test_merge_and_rank_fallback_uses_category_weights(monkeypatch) -> None:
    class FailingCompletions:
        async def create(self, **kwargs):
            raise RuntimeError("LLM unavailable")

    class FailingChat:
        completions = FailingCompletions()

    class FailingClient:
        chat = FailingChat()

    monkeypatch.setattr(summarizer, "_create_client", lambda settings, proxy=None: FailingClient())

    result = await summarizer.merge_and_rank(
        all_news=[
            NewsItem(
                summary="高危漏洞披露",
                url="https://security.example/news",
                importance=10,
                category="网络安全",
            ),
            NewsItem(
                summary="国内重大政策发布",
                url="https://domestic.example/news",
                importance=7,
                category="国内时事",
            ),
            NewsItem(
                summary="国际重大事件进展",
                url="https://world.example/news",
                importance=6,
                category="国际时事",
            ),
        ],
        settings={"model": "test-model"},
        max_items=2,
        min_items=2,
        category_weights={
            "网络安全": 0.3,
            "国内时事": 1.8,
            "国际时事": 1.8,
        },
    )

    assert [item.category for item in result] == ["国内时事", "国际时事"]

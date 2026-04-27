import inspect
from datetime import date

import pytest
import yaml

from src import main, pipeline
from src.crawler import CrawlResult
from src.summarizer import NewsItem


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict] = []

    def add_job(self, func, trigger, **kwargs) -> None:
        self.jobs.append({"func": func, "trigger": trigger, **kwargs})


def test_register_scheduled_jobs_splits_generate_and_push() -> None:
    scheduler = FakeScheduler()
    settings = {
        "schedule": {
            "cron": "30 8 * * *",
            "push_cron": "0 9 * * *",
            "timezone": "Asia/Shanghai",
        }
    }

    schedule_info = main._register_scheduled_jobs(scheduler, settings)

    assert schedule_info.generate_cron == "30 8 * * *"
    assert schedule_info.push_cron == "0 9 * * *"
    assert schedule_info.timezone == "Asia/Shanghai"
    assert [job["id"] for job in scheduler.jobs] == [
        "daily_brief_generate",
        "daily_brief_push",
    ]
    assert scheduler.jobs[0]["kwargs"] == {"send_notification": False}
    assert scheduler.jobs[1].get("kwargs") is None


def test_generate_daily_brief_defaults_to_sending_notifications() -> None:
    signature = inspect.signature(pipeline.generate_daily_brief)

    assert signature.parameters["send_notification"].default is True


@pytest.mark.asyncio
async def test_push_daily_brief_reads_today_report_and_pushes_enabled_channels(
    tmp_path, monkeypatch
) -> None:
    config_dir = tmp_path / "config"
    output_dir = tmp_path / "output"
    config_dir.mkdir()
    output_dir.mkdir()

    settings = {
        "network": {
            "proxy": "http://127.0.0.1:7890",
            "enable_for_pusher": True,
        },
        "output": {"dir": "output"},
        "pushers": {
            "dingtalk": {"enabled": True, "webhook_url": "https://dingtalk.example"},
            "feishu": {"enabled": True, "webhook_url": "https://feishu.example"},
        },
        "alert": {"enabled": True},
    }
    (config_dir / "settings.yaml").write_text(
        yaml.safe_dump(settings, allow_unicode=True), encoding="utf-8"
    )
    (output_dir / "2026-04-27.md").write_text("今日简报\n\n1. 测试新闻", encoding="utf-8")

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 4, 27)

    pushes: list[tuple[str, str, str, str | None]] = []

    class FakeDingTalkPusher:
        def __init__(self, webhook_url=None, proxy=None) -> None:
            self.webhook_url = webhook_url
            self.proxy = proxy

        async def push(self, title: str, content: str) -> bool:
            pushes.append(("dingtalk", title, content, self.proxy))
            return True

    class FakeFeishuPusher:
        def __init__(self, webhook_url=None, proxy=None) -> None:
            self.webhook_url = webhook_url
            self.proxy = proxy

        async def push(self, title: str, content: str) -> bool:
            pushes.append(("feishu", title, content, self.proxy))
            return True

    monkeypatch.setattr(pipeline, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "date", FixedDate)
    monkeypatch.setattr(pipeline, "DingTalkPusher", FakeDingTalkPusher)
    monkeypatch.setattr(pipeline, "FeishuPusher", FakeFeishuPusher)

    result = await pipeline.push_daily_brief()

    assert result is True
    assert pushes == [
        ("dingtalk", "今日简报", "今日简报\n\n1. 测试新闻", "http://127.0.0.1:7890"),
        ("feishu", "今日简报", "今日简报\n\n1. 测试新闻", "http://127.0.0.1:7890"),
    ]


@pytest.mark.asyncio
async def test_generate_daily_brief_can_skip_notifications(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {},
                "crawler": {"select_count": 0},
                "brief": {"max_items": 1, "min_items": 1},
                "output": {"dir": "output"},
                "store": {"db_path": "data/test.db", "max_db_size_mb": 50},
                "pushers": {
                    "dingtalk": {"enabled": True, "webhook_url": "https://dingtalk.example"},
                    "feishu": {"enabled": True, "webhook_url": "https://feishu.example"},
                },
                "alert": {"enabled": False},
                "network": {},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(
            {"sources": [{"name": "测试源", "url": "https://example.com", "category": "测试"}]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 4, 27)

    async def fake_crawl_sources(*args, **kwargs):
        return [
            CrawlResult(
                source_name="测试源",
                category="测试",
                url="https://example.com",
                markdown="测试新闻内容",
                success=True,
            )
        ]

    async def fake_extract_news(*args, **kwargs):
        return [NewsItem(summary="测试新闻摘要", url="https://example.com/news", importance=9)]

    async def fake_merge_and_rank(**kwargs):
        return kwargs["all_news"]

    pushes: list[tuple[str, str]] = []

    class FakeDingTalkPusher:
        def __init__(self, webhook_url=None, proxy=None) -> None:
            pass

        async def push(self, title: str, content: str) -> bool:
            pushes.append(("dingtalk", title))
            return True

    class FakeFeishuPusher:
        def __init__(self, webhook_url=None, proxy=None) -> None:
            pass

        async def push(self, title: str, content: str) -> bool:
            pushes.append(("feishu", title))
            return True

    monkeypatch.setattr(pipeline, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "date", FixedDate)
    monkeypatch.setattr(pipeline, "crawl_sources", fake_crawl_sources)
    monkeypatch.setattr(pipeline, "extract_news", fake_extract_news)
    monkeypatch.setattr(pipeline, "merge_and_rank", fake_merge_and_rank)
    monkeypatch.setattr(pipeline, "DingTalkPusher", FakeDingTalkPusher)
    monkeypatch.setattr(pipeline, "FeishuPusher", FakeFeishuPusher)

    await pipeline.generate_daily_brief(send_notification=False)

    assert (tmp_path / "output" / "2026-04-27.md").exists()
    assert pushes == []

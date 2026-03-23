"""云雀简报 — 主入口：串联爬取 → 总结 → 组装 → 保存 → 推送"""

import asyncio
import logging
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.crawler import crawl_sources
from src.summarizer import extract_news, merge_and_rank
from src.composer import compose_brief
from src.pusher import DingTalkPusher

logger = logging.getLogger(__name__)

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict:
    """加载 YAML 配置文件"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def generate_daily_brief():
    """生成每日简报的完整流程"""
    # 0. 加载环境变量
    load_dotenv(ROOT_DIR / ".env")

    # 1. 加载配置
    settings = _load_yaml(ROOT_DIR / "config" / "settings.yaml")
    sources_cfg = _load_yaml(ROOT_DIR / "config" / "sources.yaml")
    sources = sources_cfg.get("sources", [])

    llm_settings = settings.get("llm", {})
    crawler_settings = settings.get("crawler", {})
    brief_settings = settings.get("brief", {})
    pusher_settings = settings.get("pushers", {})

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("========== 云雀简报 — 开始生成 ==========")

    # 2. 并发爬取
    crawl_results = await crawl_sources(
        sources=sources,
        headless=crawler_settings.get("headless", True),
        filter_threshold=crawler_settings.get("filter_threshold", 0.45),
    )

    # 检查爬取结果
    success_results = [r for r in crawl_results if r.success and r.markdown]
    if not success_results:
        logger.error("全部资讯源爬取失败，终止流程")
        return

    logger.info("成功爬取 %d/%d 个源", len(success_results), len(crawl_results))

    # 3. LLM 单源提取
    all_news = []
    for result in success_results:
        news_items = await extract_news(
            source_name=result.source_name,
            category=result.category,
            markdown=result.markdown,
            settings=llm_settings,
        )
        all_news.extend(news_items)

    if not all_news:
        logger.error("所有源的 LLM 提取均失败，终止流程")
        return

    logger.info("共提取 %d 条新闻，开始去重排序", len(all_news))

    # 4. 去重排序
    max_items = brief_settings.get("max_items", 15)
    min_items = brief_settings.get("min_items", 10)
    ranked_news = await merge_and_rank(
        all_news=all_news,
        settings=llm_settings,
        max_items=max_items,
        min_items=min_items,
    )

    if not ranked_news:
        logger.error("去重排序后无有效新闻，终止流程")
        return

    logger.info("最终选取 %d 条新闻", len(ranked_news))

    # 5. 组装简报
    today = date.today()
    brief_md = compose_brief(ranked_news, today)

    # 6. 保存文件
    output_dir = ROOT_DIR / settings.get("output", {}).get("dir", "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{today.isoformat()}.md"
    output_file.write_text(brief_md, encoding="utf-8")
    logger.info("✅ 简报已保存: %s", output_file)

    # 7. 推送到钉钉
    dingtalk_cfg = pusher_settings.get("dingtalk", {})
    if dingtalk_cfg.get("enabled", False):
        pusher = DingTalkPusher(webhook_url=dingtalk_cfg.get("webhook_url"))
        await pusher.push(title="今日简报", content=brief_md)
    else:
        logger.info("钉钉推送未启用，跳过")

    logger.info("========== 云雀简报 — 生成完毕 ==========")


def main():
    """CLI 入口"""
    asyncio.run(generate_daily_brief())


if __name__ == "__main__":
    main()

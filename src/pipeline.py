"""云雀简报 — 核心管线：爬取 → LLM 总结 → 组装 → 保存 → 推送"""

import asyncio
import logging
import time
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.composer import compose_brief
from src.crawler import CrawlResult, crawl_sources, select_sources
from src.feed import fetch_feeds
from src.pusher import DingTalkPusher, FeishuPusher
from src.store import Store
from src.summarizer import deduplicate_by_similarity, extract_news, merge_and_rank

logger = logging.getLogger(__name__)

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent


def load_yaml(path: Path) -> dict[str, Any]:
    """加载 YAML 配置文件"""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict):
        return data
    return {}


async def _push_alert(
    pusher_settings: dict[str, Any],
    message: str,
    proxy: str | None = None,
) -> None:
    """通过已启用的推送渠道发送告警消息"""
    dingtalk_cfg = pusher_settings.get("dingtalk", {})
    if dingtalk_cfg.get("enabled", False):
        pusher = DingTalkPusher(
            webhook_url=dingtalk_cfg.get("webhook_url"),
            proxy=proxy,
        )
        await pusher.push(title="⚠️ 云雀简报告警", content=message)

    feishu_cfg = pusher_settings.get("feishu", {})
    if feishu_cfg.get("enabled", False):
        fs_pusher = FeishuPusher(
            webhook_url=feishu_cfg.get("webhook_url"),
            proxy=proxy,
        )
        await fs_pusher.push(title="⚠️ 云雀简报告警", content=message)


def _get_pusher_proxy(settings: dict[str, Any]) -> str | None:
    """根据网络配置返回推送代理地址"""
    network_settings = settings.get("network", {})
    proxy = network_settings.get("proxy")
    if proxy and network_settings.get("enable_for_pusher"):
        return proxy
    return None


async def _push_brief_content(
    pusher_settings: dict[str, Any],
    brief_md: str,
    proxy: str | None = None,
) -> bool:
    """推送简报内容到已启用渠道，返回是否全部成功"""
    results: list[bool] = []

    dingtalk_cfg = pusher_settings.get("dingtalk", {})
    if dingtalk_cfg.get("enabled", False):
        pusher = DingTalkPusher(
            webhook_url=dingtalk_cfg.get("webhook_url"),
            proxy=proxy,
        )
        results.append(await pusher.push(title="今日简报", content=brief_md))
    else:
        logger.info("钉钉推送未启用，跳过")

    feishu_cfg = pusher_settings.get("feishu", {})
    if feishu_cfg.get("enabled", False):
        fs_pusher = FeishuPusher(
            webhook_url=feishu_cfg.get("webhook_url"),
            proxy=proxy,
        )
        results.append(await fs_pusher.push(title="今日简报", content=brief_md))
    else:
        logger.info("飞书推送未启用，跳过")

    return all(results) if results else True


async def push_daily_brief() -> bool:
    """读取当天已生成简报并推送到各渠道"""
    load_dotenv(ROOT_DIR / ".env")

    settings = load_yaml(ROOT_DIR / "config" / "settings.yaml")
    pusher_settings = settings.get("pushers", {})
    alert_settings = settings.get("alert", {})
    pusher_proxy = _get_pusher_proxy(settings)

    today = date.today()
    output_dir = ROOT_DIR / settings.get("output", {}).get("dir", "output")
    output_file = output_dir / f"{today.isoformat()}.md"

    if not output_file.exists():
        message = f"⚠️ 今日简报文件不存在，无法发送通知: {output_file}"
        logger.error(message)
        if alert_settings.get("enabled", False):
            await _push_alert(pusher_settings, message, proxy=pusher_proxy)
        return False

    brief_md = output_file.read_text(encoding="utf-8")
    logger.info("开始推送今日简报: %s", output_file)
    success = await _push_brief_content(pusher_settings, brief_md, proxy=pusher_proxy)
    if success:
        logger.info("今日简报通知发送完成")
    else:
        logger.warning("今日简报通知存在发送失败的渠道")
    return success


async def generate_daily_brief(send_notification: bool = True) -> None:
    """生成每日简报的完整流程"""
    # 0. 加载环境变量
    load_dotenv(ROOT_DIR / ".env")

    # 1. 加载配置
    settings = load_yaml(ROOT_DIR / "config" / "settings.yaml")
    sources_cfg = load_yaml(ROOT_DIR / "config" / "sources.yaml")
    sources = sources_cfg.get("sources", [])

    llm_settings = settings.get("llm", {})
    crawler_settings = settings.get("crawler", {})
    brief_settings = settings.get("brief", {})
    pusher_settings = settings.get("pushers", {})
    store_settings = settings.get("store", {})
    alert_settings = settings.get("alert", {})
    network_settings = settings.get("network", {})

    proxy = network_settings.get("proxy")
    crawler_proxy = proxy if proxy and network_settings.get("enable_for_crawler") else None
    llm_proxy = proxy if proxy and network_settings.get("enable_for_llm") else None
    pusher_proxy = _get_pusher_proxy(settings)

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 初始化 SQLite 存储
    db_path = ROOT_DIR / store_settings.get("db_path", "data/lark-brief.db")
    store = Store(db_path=db_path, max_size_mb=store_settings.get("max_db_size_mb", 50))

    today_str = date.today().isoformat()
    run_id = store.start_run(today_str, total_configured=len(sources))
    start_time = time.time()

    logger.info("========== 云雀简报 — 开始生成 (run_id=%d) ==========", run_id)

    try:
        # 1.5 随机选源（保证分类覆盖）
        select_count = crawler_settings.get("select_count", 0)
        category_weights = crawler_settings.get("category_weights", {})
        selected_sources = select_sources(
            sources,
            select_count,
            category_weights=category_weights,
        )

        # 2. 按类型分流：RSS Feed 获取 + 网页爬取
        web_sources = [s for s in selected_sources if s.get("type", "web") != "rss"]
        rss_sources = [s for s in selected_sources if s.get("type") == "rss"]

        crawl_results: list[CrawlResult] = []

        if rss_sources:
            feed_settings = settings.get("feed", {})
            feed_results = await fetch_feeds(
                sources=rss_sources,
                timeout=feed_settings.get("timeout", 30),
                max_entries=feed_settings.get("max_entries", 20),
                proxy=crawler_proxy,
            )
            crawl_results.extend(feed_results)

        if web_sources:
            web_results = await crawl_sources(
                sources=web_sources,
                headless=crawler_settings.get("headless", True),
                filter_threshold=crawler_settings.get("filter_threshold", 0.45),
                page_timeout=crawler_settings.get("page_timeout", 60000),
                retry_count=crawler_settings.get("retry_count", 0),
                proxy=crawler_proxy,
            )
            crawl_results.extend(web_results)

        # 记录每源爬取结果
        for r in crawl_results:
            store.log_source(
                run_id=run_id,
                source_name=r.source_name,
                url=r.url,
                success=r.success,
                error_msg=r.error or "" if not r.success else "",
                char_count=len(r.markdown) if r.markdown else 0,
            )

        success_results = [r for r in crawl_results if r.success and r.markdown]
        if not success_results:
            logger.error("全部资讯源爬取失败，终止流程")
            store.finish_run(run_id, len(crawl_results), 0, 0, start_time, "failed")
            if alert_settings.get("enabled", False):
                await _push_alert(pusher_settings, "⚠️ 云雀简报全部资讯源爬取失败，请检查网络或源配置。", proxy=pusher_proxy)
            return

        logger.info("成功爬取 %d/%d 个源", len(success_results), len(crawl_results))

        # 检查成功率并告警
        success_rate = len(success_results) / len(crawl_results)
        min_rate = alert_settings.get("min_success_rate", 0.5)
        if alert_settings.get("enabled", False) and success_rate < min_rate:
            failed_names = [r.source_name for r in crawl_results if not r.success or not r.markdown]
            alert_msg = (
                f"⚠️ 爬取成功率偏低: {len(success_results)}/{len(crawl_results)} "
                f"({success_rate:.0%} < {min_rate:.0%})\n\n"
                f"失败源: {', '.join(failed_names)}"
            )
            await _push_alert(pusher_settings, alert_msg, proxy=pusher_proxy)

        # 3. LLM 单源提取（并行）
        extract_tasks = [
            extract_news(
                source_name=result.source_name,
                category=result.category,
                markdown=result.markdown,
                settings=llm_settings,
                proxy=llm_proxy,
            )
            for result in success_results
        ]
        news_per_source = await asyncio.gather(*extract_tasks)
        all_news = [item for items in news_per_source for item in items]

        # 更新每源新闻条数
        for result, items in zip(success_results, news_per_source, strict=True):
            store.log_source(
                run_id=run_id,
                source_name=f"{result.source_name}[LLM]",
                url=result.url,
                success=len(items) > 0,
                news_count=len(items),
            )

        if not all_news:
            logger.error("所有源的 LLM 提取均失败，终止流程")
            store.finish_run(
                run_id, len(crawl_results), len(success_results), 0, start_time, "failed"
            )
            return

        logger.info("共提取 %d 条新闻，开始历史去重", len(all_news))

        # 3.5 历史去重：URL 精确过滤
        historical_urls = store.get_recent_news_urls(days=7)
        if historical_urls:
            before_count = len(all_news)
            all_news = [item for item in all_news if item.url not in historical_urls]
            filtered_count = before_count - len(all_news)
            if filtered_count > 0:
                logger.info("URL 去重: 过滤 %d 条历史重复新闻，剩余 %d 条", filtered_count, len(all_news))

        if not all_news:
            logger.warning("URL 去重后无新闻，终止流程")
            store.finish_run(
                run_id, len(crawl_results), len(success_results), 0, start_time, "success"
            )
            return

        # 3.6 文本相似度预去重（快速过滤跨源重复和历史相似新闻）
        historical_summaries = store.get_recent_news_summaries(days=3)
        before_sim = len(all_news)
        all_news = deduplicate_by_similarity(
            all_news,
            historical_summaries=historical_summaries if historical_summaries else None,
        )
        if before_sim != len(all_news):
            logger.info("文本去重: %d → %d 条", before_sim, len(all_news))

        if not all_news:
            logger.warning("文本去重后无新闻，终止流程")
            store.finish_run(
                run_id, len(crawl_results), len(success_results), 0, start_time, "success"
            )
            return

        # 4. LLM 去重排序
        logger.info("开始 LLM 去重排序（历史摘要 %d 条，当前新闻 %d 条）", len(historical_summaries), len(all_news))
        max_items = brief_settings.get("max_items", 15)
        min_items = brief_settings.get("min_items", 10)
        ranked_news = await merge_and_rank(
            all_news=all_news,
            settings=llm_settings,
            max_items=max_items,
            min_items=min_items,
            proxy=llm_proxy,
            historical_summaries=historical_summaries if historical_summaries else None,
            category_weights=category_weights,
        )

        if not ranked_news:
            logger.error("去重排序后无有效新闻，终止流程")
            store.finish_run(
                run_id, len(crawl_results), len(success_results), 0, start_time, "failed"
            )
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

        # 6.5 保存新闻到历史表（用于后续历史去重）
        store.save_news_history(
            today_str,
            [{"summary": n.summary, "url": n.url} for n in ranked_news],
        )

        # 7. 推送到各渠道
        if send_notification:
            await _push_brief_content(pusher_settings, brief_md, proxy=pusher_proxy)
        else:
            logger.info("定时生成任务已关闭即时通知，等待独立推送任务发送")

        # 8. 完成运行记录
        stats = store.finish_run(
            run_id, len(crawl_results), len(success_results),
            len(ranked_news), start_time, "success",
        )
        logger.info(
            "========== 云雀简报 — 生成完毕 (耗时 %.1fs, 成功率 %.0f%%) ==========",
            stats.duration_sec,
            stats.success_rate * 100,
        )

    except Exception:
        store.finish_run(
            run_id, len(sources), 0, 0, start_time, "error",
        )
        logger.exception("❌ 云雀简报运行异常")
        if alert_settings.get("enabled", False):
            network_settings = settings.get("network", {}) if 'settings' in locals() else {}
            proxy = network_settings.get("proxy")
            pusher_proxy = proxy if proxy and network_settings.get("enable_for_pusher") else None
            await _push_alert(pusher_settings, "❌ 云雀简报运行异常，请查看日志。", proxy=pusher_proxy)
    finally:
        # 清理过大的数据库文件和过期历史新闻
        store.cleanup_old_news_history(keep_days=30)
        store.cleanup_if_needed()
        store.close()

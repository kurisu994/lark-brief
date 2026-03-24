"""云雀简报 — 主入口：串联爬取 → 总结 → 组装 → 保存 → 推送，支持定时调度"""

import argparse
import asyncio
import logging
import signal
import time
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.composer import compose_brief
from src.crawler import crawl_sources
from src.pusher import DingTalkPusher, FeishuPusher
from src.store import Store
from src.summarizer import extract_news, merge_and_rank

logger = logging.getLogger(__name__)

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict[str, Any]:
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


async def generate_daily_brief() -> None:
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
    store_settings = settings.get("store", {})
    alert_settings = settings.get("alert", {})
    network_settings = settings.get("network", {})

    proxy = network_settings.get("proxy")
    crawler_proxy = proxy if proxy and network_settings.get("enable_for_crawler") else None
    llm_proxy = proxy if proxy and network_settings.get("enable_for_llm") else None
    pusher_proxy = proxy if proxy and network_settings.get("enable_for_pusher") else None

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 初始化 SQLite 存储
    db_path = ROOT_DIR / store_settings.get("db_path", "data/lark-brief.db")
    store = Store(db_path=db_path, max_size_mb=store_settings.get("max_db_size_mb", 50))

    today_str = date.today().isoformat()
    run_id = store.start_run(today_str)
    start_time = time.time()

    logger.info("========== 云雀简报 — 开始生成 (run_id=%d) ==========", run_id)

    try:
        # 2. 并发爬取
        crawl_results = await crawl_sources(
            sources=sources,
            headless=crawler_settings.get("headless", True),
            filter_threshold=crawler_settings.get("filter_threshold", 0.45),
            page_timeout=crawler_settings.get("page_timeout", 60000),
            retry_count=crawler_settings.get("retry_count", 0),
            proxy=crawler_proxy,
        )

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
            # 发送告警
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

        logger.info("共提取 %d 条新闻，开始去重排序", len(all_news))

        # 4. 去重排序
        max_items = brief_settings.get("max_items", 15)
        min_items = brief_settings.get("min_items", 10)
        ranked_news = await merge_and_rank(
            all_news=all_news,
            settings=llm_settings,
            max_items=max_items,
            min_items=min_items,
            proxy=llm_proxy,
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

        # 7. 推送到各渠道
        dingtalk_cfg = pusher_settings.get("dingtalk", {})
        if dingtalk_cfg.get("enabled", False):
            pusher = DingTalkPusher(
                webhook_url=dingtalk_cfg.get("webhook_url"),
                proxy=pusher_proxy,
            )
            await pusher.push(title="今日简报", content=brief_md)
        else:
            logger.info("钉钉推送未启用，跳过")

        feishu_cfg = pusher_settings.get("feishu", {})
        if feishu_cfg.get("enabled", False):
            fs_pusher = FeishuPusher(
                webhook_url=feishu_cfg.get("webhook_url"),
                proxy=pusher_proxy,
            )
            await fs_pusher.push(title="今日简报", content=brief_md)
        else:
            logger.info("飞书推送未启用，跳过")

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
            # 这时推送可能会因为局部作用域找不到 proxy 配置，我们捕获配置
            network_settings = settings.get("network", {}) if 'settings' in locals() else {}
            proxy = network_settings.get("proxy")
            pusher_proxy = proxy if proxy and network_settings.get("enable_for_pusher") else None
            await _push_alert(pusher_settings, "❌ 云雀简报运行异常，请查看日志。", proxy=pusher_proxy)
    finally:
        # 清理过大的数据库文件
        store.cleanup_if_needed()
        store.close()


def _run_scheduler(settings_path: Path) -> None:
    """以定时调度模式运行"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    settings = _load_yaml(settings_path)
    schedule_cfg = settings.get("schedule", {})
    cron_expr = schedule_cfg.get("cron", "0 8 * * *")
    timezone = schedule_cfg.get("timezone", "Asia/Shanghai")

    # 解析 cron 表达式（分 时 日 月 周）
    parts = cron_expr.split()
    trigger = CronTrigger(
        minute=parts[0] if len(parts) > 0 else "0",
        hour=parts[1] if len(parts) > 1 else "8",
        day=parts[2] if len(parts) > 2 else "*",
        month=parts[3] if len(parts) > 3 else "*",
        day_of_week=parts[4] if len(parts) > 4 else "*",
        timezone=timezone,
    )

    # 先创建并设置事件循环，AsyncIOScheduler.start() 需要活跃的循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(generate_daily_brief, trigger, id="daily_brief", name="每日简报生成")
    scheduler.start()

    logger.info("📅 定时调度已启动: cron='%s', timezone='%s'", cron_expr, timezone)
    logger.info("下次执行时间: %s", scheduler.get_job("daily_brief").next_run_time)

    # 优雅退出
    def _shutdown(sig: int, frame: object) -> None:
        logger.info("收到信号 %s，正在停止调度器...", sig)
        scheduler.shutdown(wait=False)
        loop.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_forever()
    finally:
        loop.close()


def main() -> None:
    """CLI 入口：支持 --once（默认）和 --schedule 两种模式"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="云雀简报 — 每日资讯简报生成工具")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="以定时调度模式运行（使用 settings.yaml 中的 cron 配置）",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="启动 Web UI 服务",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Web UI 服务端口（默认 8080）",
    )
    args = parser.parse_args()

    if args.web:
        import uvicorn
        import yaml

        settings_path = ROOT_DIR / "config" / "settings.yaml"
        with open(settings_path, encoding="utf-8") as f:
            settings = yaml.safe_load(f) or {}

        from src.web import create_app

        app = create_app(settings)
        logger.info("启动 Web UI: http://0.0.0.0:%d", args.port)
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    elif args.schedule:
        settings_path = ROOT_DIR / "config" / "settings.yaml"
        _run_scheduler(settings_path)
    else:
        asyncio.run(generate_daily_brief())


if __name__ == "__main__":
    main()

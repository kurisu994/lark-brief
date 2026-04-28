"""云雀简报 — CLI 入口：支持 --web / --schedule / 默认单次三种模式"""

import argparse
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent


def _parse_cron(cron_expr: str, timezone: str = "Asia/Shanghai") -> "CronTrigger":
    """将 cron 表达式解析为 APScheduler CronTrigger"""
    from apscheduler.triggers.cron import CronTrigger

    parts = cron_expr.split()
    return CronTrigger(
        minute=parts[0] if len(parts) > 0 else "0",
        hour=parts[1] if len(parts) > 1 else "8",
        day=parts[2] if len(parts) > 2 else "*",
        month=parts[3] if len(parts) > 3 else "*",
        day_of_week=parts[4] if len(parts) > 4 else "*",
        timezone=timezone,
    )


def _setup_scheduler(settings: dict) -> "AsyncIOScheduler":
    """根据配置创建并注册双定时任务的调度器（生成 + 推送）"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from src.pipeline import generate_daily_brief, push_daily_brief

    schedule_cfg = settings.get("schedule", {})
    timezone = schedule_cfg.get("timezone", "Asia/Shanghai")
    generate_cron = schedule_cfg.get("generate_cron", "30 8 * * *")
    push_cron = schedule_cfg.get("push_cron", "0 9 * * *")

    scheduler = AsyncIOScheduler()

    # 生成任务：爬取 + LLM 摘要 + 保存文件，不发送通知
    generate_trigger = _parse_cron(generate_cron, timezone)
    scheduler.add_job(
        generate_daily_brief,
        generate_trigger,
        kwargs={"send_notification": False},
        id="daily_generate",
        name="每日简报生成",
    )

    # 推送任务：读取当天已生成的简报文件并发送通知
    push_trigger = _parse_cron(push_cron, timezone)
    scheduler.add_job(
        push_daily_brief,
        push_trigger,
        id="daily_push",
        name="每日简报推送",
    )

    return scheduler, generate_cron, push_cron, timezone


def _run_scheduler(settings_path: Path) -> None:
    """以纯定时调度模式运行（无 Web 服务）"""
    from src.pipeline import load_yaml

    settings = load_yaml(settings_path)

    async def async_main() -> None:
        scheduler, gen_cron, push_cron, tz = _setup_scheduler(settings)
        scheduler.start()

        logger.info("📅 定时调度已启动 (timezone='%s')", tz)
        logger.info("  生成任务: cron='%s', 下次执行: %s", gen_cron, scheduler.get_job("daily_generate").next_run_time)
        logger.info("  推送任务: cron='%s', 下次执行: %s", push_cron, scheduler.get_job("daily_push").next_run_time)

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            scheduler.shutdown(wait=False)

    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("收到退出信号，调度任务已停止")


def _run_web(port: int) -> None:
    """启动 Web API 服务（内嵌定时调度）"""
    import uvicorn

    from src.pipeline import load_yaml
    from src.web import create_app

    settings_path = ROOT_DIR / "config" / "settings.yaml"
    settings = load_yaml(settings_path)

    app = create_app(settings)

    @asynccontextmanager
    async def lifespan_with_scheduler(application):
        """在 Web 服务启动时同时启动定时调度"""
        scheduler, gen_cron, push_cron, tz = _setup_scheduler(settings)
        scheduler.start()
        logger.info("📅 定时调度已启动 (timezone='%s')", tz)
        logger.info("  生成任务: cron='%s', 下次执行: %s", gen_cron, scheduler.get_job("daily_generate").next_run_time)
        logger.info("  推送任务: cron='%s', 下次执行: %s", push_cron, scheduler.get_job("daily_push").next_run_time)
        try:
            yield
        finally:
            scheduler.shutdown(wait=False)
            logger.info("定时调度已停止")

    app.router.lifespan_context = lifespan_with_scheduler

    logger.info("启动 Web API + 定时调度: http://0.0.0.0:%d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)


def main() -> None:
    """CLI 入口"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="云雀简报 — 每日资讯简报生成工具")
    parser.add_argument("--schedule", action="store_true", help="以定时调度模式运行")
    parser.add_argument("--web", action="store_true", help="启动 Web API 服务（含定时调度）")
    parser.add_argument("--port", type=int, default=8080, help="Web 服务端口（默认 8080）")
    args = parser.parse_args()

    if args.web:
        _run_web(args.port)
    elif args.schedule:
        _run_scheduler(ROOT_DIR / "config" / "settings.yaml")
    else:
        from src.pipeline import generate_daily_brief
        asyncio.run(generate_daily_brief())


if __name__ == "__main__":
    main()

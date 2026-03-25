"""云雀简报 — CLI 入口：支持 --web / --schedule / 默认单次三种模式"""

import argparse
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent


def _parse_cron(settings: dict) -> "CronTrigger":
    """从配置中解析 cron 触发器"""
    from apscheduler.triggers.cron import CronTrigger

    schedule_cfg = settings.get("schedule", {})
    cron_expr = schedule_cfg.get("cron", "0 8 * * *")
    timezone = schedule_cfg.get("timezone", "Asia/Shanghai")
    parts = cron_expr.split()
    return CronTrigger(
        minute=parts[0] if len(parts) > 0 else "0",
        hour=parts[1] if len(parts) > 1 else "8",
        day=parts[2] if len(parts) > 2 else "*",
        month=parts[3] if len(parts) > 3 else "*",
        day_of_week=parts[4] if len(parts) > 4 else "*",
        timezone=timezone,
    )


def _run_scheduler(settings_path: Path) -> None:
    """以纯定时调度模式运行（无 Web 服务）"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from src.pipeline import generate_daily_brief, load_yaml

    settings = load_yaml(settings_path)
    trigger = _parse_cron(settings)
    schedule_cfg = settings.get("schedule", {})
    cron_expr = schedule_cfg.get("cron", "0 8 * * *")
    timezone = schedule_cfg.get("timezone", "Asia/Shanghai")

    async def async_main() -> None:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(generate_daily_brief, trigger, id="daily_brief", name="每日简报生成")
        scheduler.start()

        logger.info("📅 定时调度已启动: cron='%s', timezone='%s'", cron_expr, timezone)
        logger.info("下次执行时间: %s", scheduler.get_job("daily_brief").next_run_time)

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
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from src.pipeline import generate_daily_brief, load_yaml
    from src.web import create_app

    settings_path = ROOT_DIR / "config" / "settings.yaml"
    settings = load_yaml(settings_path)
    trigger = _parse_cron(settings)
    schedule_cfg = settings.get("schedule", {})
    cron_expr = schedule_cfg.get("cron", "0 8 * * *")
    timezone = schedule_cfg.get("timezone", "Asia/Shanghai")

    app = create_app(settings)

    @asynccontextmanager
    async def lifespan_with_scheduler(application):
        """在 Web 服务启动时同时启动定时调度"""
        scheduler = AsyncIOScheduler()
        scheduler.add_job(generate_daily_brief, trigger, id="daily_brief", name="每日简报生成")
        scheduler.start()
        logger.info("📅 定时调度已启动: cron='%s', timezone='%s'", cron_expr, timezone)
        logger.info("下次执行时间: %s", scheduler.get_job("daily_brief").next_run_time)
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

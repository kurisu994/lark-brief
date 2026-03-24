"""路由注册：页面路由（SSR）+ 数据 API（JSON）"""

import asyncio
import math
import re
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.store import Store

from .deps import get_output_dir, get_store, get_templates
from .i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES

# 简报生成任务锁，防止重复触发
_generate_lock = asyncio.Lock()
_generate_task: asyncio.Task[None] | None = None


def register_routes(app: FastAPI) -> None:
    """注册所有页面路由和 API 路由"""

    # ========== 页面路由（SSR） ==========

    @app.get("/", response_class=HTMLResponse)
    async def index_page(
        request: Request,
        page: int = 1,
        size: int = 20,
        store: Store = Depends(get_store),
        templates: Jinja2Templates = Depends(get_templates),
    ) -> HTMLResponse:
        """简报列表页"""
        offset = (page - 1) * size
        runs = store.list_runs(limit=size, offset=offset)
        total = store.count_runs()
        total_pages = max(1, math.ceil(total / size))

        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "runs": runs,
                "page": page,
                "size": size,
                "total": total,
                "total_pages": total_pages,
            },
        )

    @app.get("/brief/{date}", response_class=HTMLResponse)
    async def brief_page(
        request: Request,
        date: str,
        store: Store = Depends(get_store),
        templates: Jinja2Templates = Depends(get_templates),
        output_dir: Path = Depends(get_output_dir),
    ) -> HTMLResponse:
        """简报详情页"""
        run = store.get_run_by_date(date)
        sources: list[dict] = []
        brief_md = ""

        if run:
            sources = store.get_source_logs(run["id"])

        # 读取简报 MD 文件
        md_file = output_dir / f"{date}.md"
        if md_file.exists():
            brief_md = md_file.read_text(encoding="utf-8")

        # 日期不存在且无文件 → 404
        if not run and not brief_md:
            return templates.TemplateResponse(
                request, "404.html", status_code=404
            )

        return templates.TemplateResponse(
            request,
            "brief.html",
            {
                "date": date,
                "run": run,
                "sources": sources,
                "brief_md": brief_md,
            },
        )

    # ========== 数据 API（JSON） ==========

    @app.get("/api/briefs")
    async def api_list_briefs(
        page: int = 1,
        size: int = 20,
        store: Store = Depends(get_store),
        output_dir: Path = Depends(get_output_dir),
    ) -> JSONResponse:
        """简报列表 API"""
        offset = (page - 1) * size
        runs = store.list_runs(limit=size, offset=offset)
        total = store.count_runs()

        items = []
        for run in runs:
            total_src = run.get("total_sources", 0)
            success_cnt = run.get("success_count", 0)
            md_file = output_dir / f"{run['run_date']}.md"
            items.append({
                **run,
                "success_rate": round(success_cnt / total_src, 2) if total_src > 0 else 0,
                "has_brief": md_file.exists(),
            })

        return JSONResponse({
            "items": items,
            "total": total,
            "page": page,
            "size": size,
        })

    @app.get("/api/briefs/{date}")
    async def api_brief_detail(
        date: str,
        store: Store = Depends(get_store),
        output_dir: Path = Depends(get_output_dir),
    ) -> JSONResponse:
        """简报详情 API"""
        run = store.get_run_by_date(date)
        sources: list[dict] = []
        brief_md = ""

        if run:
            sources = store.get_source_logs(run["id"])

        md_file = output_dir / f"{date}.md"
        if md_file.exists():
            brief_md = md_file.read_text(encoding="utf-8")

        if not run and not brief_md:
            return JSONResponse({"error": "Not found"}, status_code=404)

        return JSONResponse({
            "run": run,
            "sources": sources,
            "brief_md": brief_md,
        })

    @app.get("/api/runs/{run_id}/sources")
    async def api_run_sources(
        run_id: int,
        store: Store = Depends(get_store),
    ) -> JSONResponse:
        """源爬取详情 API"""
        sources = store.get_source_logs(run_id)
        return JSONResponse({"sources": sources})

    # ========== 统计页面（Phase 2） ==========

    @app.get("/stats", response_class=HTMLResponse)
    async def stats_page(
        request: Request,
        days: int = 30,
        health_days: int = 7,
        store: Store = Depends(get_store),
        templates: Jinja2Templates = Depends(get_templates),
    ) -> HTMLResponse:
        """统计面板页"""
        overview = store.get_stats_overview()
        trend = store.get_success_trend(days=days)
        sources_health = store.get_source_health(days=health_days)

        # 为每个源附加近期逐日状态
        for src in sources_health:
            src["recent"] = store.get_source_recent_status(
                src["source_name"], days=health_days
            )

        return templates.TemplateResponse(
            request,
            "stats.html",
            {
                "overview": overview,
                "trend": trend,
                "sources_health": sources_health,
                "days": days,
                "health_days": health_days,
            },
        )

    # ========== 统计 API（Phase 2） ==========

    @app.get("/api/stats/overview")
    async def api_stats_overview(
        store: Store = Depends(get_store),
    ) -> JSONResponse:
        """总体统计 API"""
        return JSONResponse(store.get_stats_overview())

    @app.get("/api/stats/trend")
    async def api_stats_trend(
        days: int = 30,
        store: Store = Depends(get_store),
    ) -> JSONResponse:
        """成功率趋势 API"""
        return JSONResponse({"days": days, "data": store.get_success_trend(days=days)})

    @app.get("/api/stats/sources")
    async def api_stats_sources(
        days: int = 7,
        store: Store = Depends(get_store),
    ) -> JSONResponse:
        """各源健康度 API"""
        health = store.get_source_health(days=days)
        for src in health:
            src["recent"] = store.get_source_recent_status(
                src["source_name"], days=days
            )
        return JSONResponse({"days": days, "data": health})

    # ========== 手动触发生成（Phase 3） ==========

    @app.post("/api/generate")
    async def api_trigger_generate(request: Request) -> JSONResponse:
        """手动触发简报生成（后台异步执行）"""
        global _generate_task

        async with _generate_lock:
            # 检查是否有正在执行的生成任务
            if _generate_task and not _generate_task.done():
                return JSONResponse(
                    {"status": "running", "message": "Briefing generation is already in progress."},
                    status_code=409,
                )

            from src.main import generate_daily_brief

            _generate_task = asyncio.create_task(generate_daily_brief())

        return JSONResponse(
            {"status": "started", "message": "Briefing generation started."},
            status_code=202,
        )

    @app.get("/api/generate/status")
    async def api_generate_status() -> JSONResponse:
        """查询生成任务状态"""
        if _generate_task is None:
            return JSONResponse({"status": "idle", "message": "No generation task has been triggered."})
        if not _generate_task.done():
            return JSONResponse({"status": "running", "message": "Generation in progress."})
        if _generate_task.cancelled():
            return JSONResponse({"status": "cancelled", "message": "Generation was cancelled."})
        exc = _generate_task.exception()
        if exc:
            return JSONResponse(
                {"status": "failed", "message": f"Generation failed: {exc!s}"},
                status_code=500,
            )
        return JSONResponse({"status": "completed", "message": "Generation completed successfully."})

    # ========== 全文搜索（Phase 3） ==========

    def _search_briefs(output_dir: Path, query: str, limit: int = 50) -> list[dict]:
        """在 output/*.md 文件中搜索关键词，返回匹配结果"""
        results: list[dict] = []
        if not query.strip():
            return results

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        md_files = sorted(output_dir.glob("*.md"), reverse=True)

        for md_file in md_files[:200]:  # 最多扫描 200 个文件
            content = md_file.read_text(encoding="utf-8")
            matches = list(pattern.finditer(content))
            if not matches:
                continue

            # 提取第一个匹配的上下文片段
            first = matches[0]
            start = max(0, first.start() - 60)
            end = min(len(content), first.end() + 60)
            snippet = content[start:end].replace("\n", " ").strip()
            if start > 0:
                snippet = "…" + snippet
            if end < len(content):
                snippet = snippet + "…"

            results.append({
                "date": md_file.stem,
                "match_count": len(matches),
                "snippet": snippet,
            })

            if len(results) >= limit:
                break

        return results

    @app.get("/api/search")
    async def api_search(
        q: str = "",
        output_dir: Path = Depends(get_output_dir),
    ) -> JSONResponse:
        """全文搜索 API"""
        results = _search_briefs(output_dir, q)
        return JSONResponse({"query": q, "total": len(results), "results": results})

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(
        request: Request,
        q: str = "",
        templates: Jinja2Templates = Depends(get_templates),
        output_dir: Path = Depends(get_output_dir),
    ) -> HTMLResponse:
        """搜索结果页"""
        results = _search_briefs(output_dir, q) if q else []
        return templates.TemplateResponse(
            request,
            "search.html",
            {"query": q, "results": results},
        )

    # ========== 语言切换（i18n） ==========

    @app.get("/api/lang/{locale}")
    async def switch_language(request: Request, locale: str) -> RedirectResponse:
        """切换界面语言，通过 Cookie 持久化"""
        if locale not in SUPPORTED_LOCALES:
            locale = DEFAULT_LOCALE
        referer = request.headers.get("referer", "/")
        response = RedirectResponse(url=referer, status_code=302)
        response.set_cookie(
            "lang", locale, max_age=365 * 24 * 3600, httponly=True, samesite="lax"
        )
        return response

    # ========== 错误处理 ==========

    @app.exception_handler(404)
    async def not_found_handler(request: Request, _exc: Exception) -> HTMLResponse:
        """404 页面"""
        templates: Jinja2Templates = request.app.state.templates
        return templates.TemplateResponse(
            request, "404.html", status_code=404
        )

    @app.exception_handler(500)
    async def server_error_handler(request: Request, _exc: Exception) -> HTMLResponse:
        """500 页面"""
        templates: Jinja2Templates = request.app.state.templates
        return templates.TemplateResponse(
            request, "500.html", status_code=500
        )

"""路由注册：页面路由（SSR）+ 数据 API（JSON）"""

import math
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.store import Store

from .deps import get_output_dir, get_store, get_templates


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

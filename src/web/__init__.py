"""Web UI 模块：提供简报浏览和运行统计的 Web 界面"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.store import Store

from .routes import register_routes

# 模块目录
_MODULE_DIR = Path(__file__).resolve().parent


def create_app(settings: dict[str, Any]) -> FastAPI:
    """创建 FastAPI 应用实例

    Args:
        settings: 从 settings.yaml 加载的全局配置
    """
    app = FastAPI(title="Lark Brief", docs_url=None, redoc_url=None)

    # 挂载静态资源
    static_dir = _MODULE_DIR / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 初始化模板引擎
    templates = Jinja2Templates(directory=str(_MODULE_DIR / "templates"))

    # 初始化 Store（只读查询）
    store_cfg = settings.get("store", {})
    root_dir = Path(__file__).resolve().parent.parent.parent
    db_path = root_dir / store_cfg.get("db_path", "data/lark-brief.db")
    store = Store(db_path=db_path, max_size_mb=store_cfg.get("max_db_size_mb", 50))

    # 输出目录
    output_dir = root_dir / settings.get("output", {}).get("dir", "output")

    # 保存到 app.state 供路由使用
    app.state.store = store
    app.state.templates = templates
    app.state.output_dir = output_dir

    # 注册路由
    register_routes(app)

    return app

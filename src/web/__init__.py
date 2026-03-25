"""Web API 模块：提供纯 JSON 接口供 Next.js 前端调用"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.store import Store

from .routes import register_routes

# 模块目录
_MODULE_DIR = Path(__file__).resolve().parent


def create_app(settings: dict[str, Any]) -> FastAPI:
    """创建 FastAPI 应用实例（纯 API 模式）

    Args:
        settings: 从 settings.yaml 加载的全局配置
    """
    app = FastAPI(title="Lark Brief API", docs_url="/docs", redoc_url=None)

    # CORS 中间件：允许前端跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制为前端域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 初始化 Store（只读查询）
    store_cfg = settings.get("store", {})
    root_dir = Path(__file__).resolve().parent.parent.parent
    db_path = root_dir / store_cfg.get("db_path", "data/lark-brief.db")
    store = Store(db_path=db_path, max_size_mb=store_cfg.get("max_db_size_mb", 50))

    # 输出目录
    output_dir = root_dir / settings.get("output", {}).get("dir", "output")

    # 保存到 app.state 供路由使用
    app.state.store = store
    app.state.output_dir = output_dir
    app.state.settings = settings

    # 注册路由
    register_routes(app)

    return app

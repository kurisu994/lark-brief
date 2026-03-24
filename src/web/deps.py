"""依赖注入：从 app.state 获取 Store、Templates 等共享实例"""

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from src.store import Store


def get_store(request: Request) -> Store:
    """获取 Store 实例"""
    return request.app.state.store  # type: ignore[no-any-return]


def get_templates(request: Request) -> Jinja2Templates:
    """获取 Jinja2 模板引擎"""
    return request.app.state.templates  # type: ignore[no-any-return]


def get_output_dir(request: Request) -> Path:
    """获取简报输出目录"""
    return request.app.state.output_dir  # type: ignore[no-any-return]

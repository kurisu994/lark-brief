"""依赖注入：从 app.state 获取 Store 等共享实例"""

from pathlib import Path

from fastapi import Request

from src.store import Store


def get_store(request: Request) -> Store:
    """获取 Store 实例"""
    return request.app.state.store  # type: ignore[no-any-return]


def get_output_dir(request: Request) -> Path:
    """获取简报输出目录"""
    return request.app.state.output_dir  # type: ignore[no-any-return]

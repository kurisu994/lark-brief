# justfile
# 使用: just <recipe>

# 默认命令：显示帮助
default:
    @just --list

# 安装依赖
install:
    uv sync

# 启动开发（运行主程序）
dev:
    uv run python -m src.main

# 以定时调度模式运行
schedule:
    uv run python -m src.main --schedule

# 启动 Web UI（默认端口 8080）
web port="8080":
    uv run lark-brief --web --port {{ port }}

# Lint 检查
lint:
    uv run ruff check src/

# Lint 检查并自动修复
fix:
    uv run ruff check src/ --fix
    uv run ruff format src/

# 类型检查
check:
    uv run mypy src/

# 完整检查（静态检查 + 类型检查）
all: lint check

# Docker 构建
docker-build:
    docker compose build

# Docker 启动（定时调度模式）
docker-up:
    docker compose up -d

# Docker 单次运行
docker-once:
    docker compose run --rm lark-brief --once

# Docker 停止
docker-down:
    docker compose down

# Docker 查看日志
docker-logs:
    docker compose logs -f --tail=50

# 清理缓存
clean:
    rm -rf .mypy_cache .ruff_cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

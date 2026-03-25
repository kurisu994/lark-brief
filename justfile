# justfile
# 使用: just <recipe>

# 默认命令：显示帮助
default:
    @just --list

# ──────────────── 后端 ────────────────

# 安装后端依赖
install:
    uv sync

# 单次生成简报
run:
    uv run python -m src.main

# 启动 Web API + 定时调度（默认端口 8080）
web port="8080":
    uv run lark-brief --web --port {{ port }}

# 以纯定时调度模式运行（无 Web）
schedule:
    uv run python -m src.main --schedule

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

# ──────────────── 前端 ────────────────

# 安装前端依赖
fe-install:
    cd frontend && pnpm install

# 启动前端开发服务器
fe-dev:
    cd frontend && pnpm dev

# 构建前端
fe-build:
    cd frontend && pnpm build

# ──────────────── Docker ────────────────

# Docker 构建所有镜像
docker-build:
    docker compose build

# Docker 启动（后端 + 前端）
docker-up:
    docker compose up -d

# Docker 单次运行简报生成
docker-once:
    docker compose run --rm backend python -m src.main

# Docker 停止
docker-down:
    docker compose down

# Docker 查看日志
docker-logs service="":
    docker compose logs -f --tail=50 {{ service }}

# ──────────────── 清理 ────────────────

# 清理缓存
clean:
    rm -rf .mypy_cache .ruff_cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 清理前端构建产物
fe-clean:
    rm -rf frontend/.next frontend/node_modules

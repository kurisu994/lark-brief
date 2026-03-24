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

# 清理缓存
clean:
    rm -rf .mypy_cache .ruff_cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

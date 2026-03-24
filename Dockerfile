# 多阶段构建：安装依赖 + Playwright 浏览器
FROM python:3.14-slim AS base

# 系统依赖（Playwright Chromium 运行所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright 浏览器运行时依赖
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libwayland-client0 \
    # lxml 编译依赖
    build-essential libxml2-dev libxslt-dev zlib1g-dev \
    # 中文字体支持
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 先复制依赖描述文件，利用 Docker 缓存
COPY pyproject.toml uv.lock ./

# 安装项目依赖（不安装项目本身）
RUN uv sync --frozen --no-install-project

# 安装 Playwright Chromium 浏览器
RUN uv run playwright install chromium

# 复制项目源码
COPY src/ ./src/
COPY config/ ./config/
COPY main.py ./

# 安装项目本身
RUN uv sync --frozen

# 创建数据目录和输出目录
RUN mkdir -p /app/data /app/output

# 挂载点
VOLUME ["/app/config", "/app/output", "/app/data"]

# 默认以定时调度模式运行
ENTRYPOINT ["uv", "run", "python", "-m", "src.main"]
CMD ["--schedule"]

# AGENTS.md — lark-brief

## 项目概述

每日资讯简报自动生成工具，四阶段管线：**爬取 → LLM 总结 → 格式化简报 MD → 推送（钉钉/飞书）**。

## 架构

采用**前后端分离**架构：后端 FastAPI 提供纯 JSON API，前端 Next.js + HeroUI 提供 Web 界面。

```
# 后端（Python）
src/main.py          # 入口，串联完整异步流程 (asyncio)，支持 --web / --schedule / 默认单次 + 成功率告警
src/crawler.py       # 爬取模块 — crawl4ai 三阶段爬取（批量→特殊源→重试）+ PruningContentFilter 去噪
src/summarizer.py    # 总结模块 — 火山引擎 LLM 并行提取摘要 + 跨源去重排序
src/composer.py      # 组装模块 — 格式化简报 MD（含 borax 农历日期）
src/pusher.py        # 推送模块 — 钉钉 & 飞书机器人 Webhook（HMAC-SHA256 加签）+ 简报美化格式
src/store.py         # 持久化模块 — SQLite 运行日志（同日覆盖）+ 文件大小自动清理
src/web/             # 纯 JSON API 模块（FastAPI + CORS）
  __init__.py        # create_app() 工厂函数 + CORS 中间件
  routes.py          # RESTful API 路由（/api/briefs, /api/stats, /api/generate, /api/search）
  deps.py            # 依赖注入（Store、OutputDir）

# 前端（TypeScript / Next.js）
frontend/            # Next.js App Router + HeroUI v3 组件库
  app/               # 页面路由
    page.tsx          # 首页：简报列表 + 生成按钮
    brief/[date]/     # 简报详情页（Markdown 渲染 + 运行信息侧栏）
    stats/            # 统计面板（KPI + 趋势 + 源健康度）
    search/           # 全文搜索
  components/        # 共享组件（导航栏等）
  lib/api.ts         # API 服务层（类型定义 + fetch 封装）
  public/favicon.ico # 站点图标

# 配置与数据
config/settings.yaml # 全局配置：LLM 端点、爬虫参数、输出路径、推送渠道
config/sources.yaml  # 资讯源列表：name/url/category/enabled
output/              # 生成的简报归档，格式 YYYY-MM-DD.md
data/                # SQLite 数据库（lark-brief.db）
```

**数据流**: `sources.yaml → crawler(CrawlResult) → summarizer(NewsItem) → composer(str) → output/*.md + pusher(钉钉/飞书)`

## 关键约定

- **前后端分离**: 后端仅提供 JSON API（`/api/*`），前端 Next.js 通过 `rewrites` 反向代理 API 请求
- **异步优先**: 爬取和 LLM 调用均为 `async`，LLM 提取使用 `asyncio.gather` 并行化，入口通过 `asyncio.run()` 驱动
- **数据类传递**: 模块间通过 `dataclass` 传递数据（`CrawlResult`、`NewsItem`），不使用裸 dict
- **LLM 协议**: 使用 `openai` SDK 连接火山引擎（只替换 `base_url`），API Key 通过环境变量 `ARK_API_KEY` 读取
- **配置与代码分离**: 所有可变参数放 YAML，代码中不硬编码资讯源或模型 ID
- **同日覆盖**: `store.start_run()` 同一天重复执行时先 DELETE 旧记录再 INSERT，确保每天只保留一条运行记录
- **定时调度**: 使用 `AsyncIOScheduler` 在标准 `asyncio` 协程内运行，避免 `no running event loop` 问题
- **告警机制**: 爬取全部失败或成功率低于阈值时，通过已启用的推送渠道发送告警消息

## 开发环境

```bash
# 后端：依赖管理使用 uv
uv sync                    # 安装依赖
uv run lark-brief --web    # 启动后端 API（端口 8080）

# 前端：依赖管理使用 pnpm
cd frontend
pnpm install                # 安装依赖
pnpm dev                    # 启动前端开发服务器（端口 3000）

# Docker 部署（双服务）
docker compose up -d       # backend(API + 调度) + web(前端)

# 必需环境变量
export ARK_API_KEY="your-volcano-engine-api-key"
```

## 核心依赖用途

| 包 | 用途 |
|---|------|
| `crawl4ai` | 异步网页爬取，`arun_many()` 并发 + `PruningContentFilter` 内容去噪 |
| `openai` | 调用火山引擎 LLM（兼容 OpenAI 协议） |
| `borax` | `borax.calendars` 生成中国农历日期 |
| `fastapi` | 后端纯 JSON API 框架（提供 CORS + Swagger /docs） |
| `uvicorn` | ASGI 服务器（运行 FastAPI 应用） |
| `apscheduler` | 定时调度（CronTrigger，`--schedule` 模式） |
| `@heroui/react` | 前端 UI 组件库（HeroUI v3，Tailwind CSS v4） |
| `next` | 前端框架（App Router，standalone 部署） |
| `react-markdown` | 简报 Markdown 渲染 |

## 注意事项

- 根目录 `main.py` 是占位文件，实际入口为 `src/main.py`
- 后端不再包含 HTML 渲染，所有页面由前端 Next.js 负责
- Docker 分两个服务：`backend`(API + 定时调度) / `web`(前端)
- 前端镜像基于 Node Alpine，体积远小于后端镜像
- 代码注释使用中文，变量/函数名使用英文

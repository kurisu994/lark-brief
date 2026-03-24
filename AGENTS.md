# AGENTS.md — lark-brief

## 项目概述

每日资讯简报自动生成工具，四阶段管线：**爬取 → LLM 总结 → 格式化简报 MD → 推送（钉钉/飞书）**。

## 架构

```
src/main.py          # 入口，串联完整异步流程 (asyncio)，支持 --web / --schedule / 默认单次 + 成功率告警
src/crawler.py       # 爬取模块 — crawl4ai 三阶段爬取（批量→特殊源→重试）+ PruningContentFilter 去噪
src/summarizer.py    # 总结模块 — 火山引擎 LLM 并行提取摘要 + 跨源去重排序
src/composer.py      # 组装模块 — 格式化简报 MD（含 borax 农历日期）
src/pusher.py        # 推送模块 — 钉钉 & 飞书机器人 Webhook（HMAC-SHA256 加签）+ 简报美化格式
src/store.py         # 持久化模块 — SQLite 运行日志（同日覆盖）+ 文件大小自动清理 + Web UI 只读查询
src/web/             # Web UI 模块 — FastAPI + Jinja2 + Tailwind（欧美极简风格）
  __init__.py        # create_app() 工厂函数
  i18n.py            # 国际化模块（中英文切换，contextvars + JSON 翻译文件）
  routes.py          # 页面路由（SSR）+ 数据 API（JSON）+ 生成/搜索/语言切换 API
  deps.py            # 依赖注入（Store、Templates、OutputDir）
  static/style.css   # 自定义 CSS（Markdown 渲染、Dark Mode）
  locales/           # 翻译文件（en.json、zh.json）
  templates/         # Jinja2 模板（base/index/brief/stats/search/404/500）
config/settings.yaml # 全局配置：LLM 端点、爬虫参数、输出路径、推送渠道
config/sources.yaml  # 资讯源列表：name/url/category/enabled
output/              # 生成的简报归档，格式 YYYY-MM-DD.md
data/                # SQLite 数据库（lark-brief.db）
```

**数据流**: `sources.yaml → crawler(CrawlResult) → summarizer(NewsItem) → composer(str) → output/*.md + pusher(钉钉/飞书)`

## 关键约定

- **异步优先**: 爬取和 LLM 调用均为 `async`，LLM 提取使用 `asyncio.gather` 并行化，入口通过 `asyncio.run()` 驱动
- **数据类传递**: 模块间通过 `dataclass` 传递数据（`CrawlResult`、`NewsItem`），不使用裸 dict
- **LLM 协议**: 使用 `openai` SDK 连接火山引擎（只替换 `base_url`），API Key 通过环境变量 `ARK_API_KEY` 读取
- **配置与代码分离**: 所有可变参数放 YAML，代码中不硬编码资讯源或模型 ID
- **简报格式固定**: 输出格式见 `docs/implementation-plan.md` §二，编号列表，全中文，10-20 条
- **同日覆盖**: `store.start_run()` 同一天重复执行时先 DELETE 旧记录再 INSERT，确保每天只保留一条运行记录
- **告警机制**: 爬取全部失败或成功率低于阈值时，通过已启用的推送渠道发送告警消息
- **LLM 降级**: 去重排序 LLM 调用失败时，自动降级为按 importance 排序取 Top N

## 开发环境

```bash
# 依赖管理使用 uv（非 pip），锁文件为 uv.lock
uv sync                    # 安装依赖
uv run python -m src.main  # 运行（或 uv run lark-brief）
uv run lark-brief --web    # 启动 Web UI（端口 8080）

# 必需环境变量
export ARK_API_KEY="your-volcano-engine-api-key"

# Python >= 3.10，版本锁定见 .python-version
```

## 核心依赖用途

| 包 | 用途 |
|---|------|
| `crawl4ai` | 异步网页爬取，`arun_many()` 并发 + `PruningContentFilter` 内容去噪 |
| `openai` | 调用火山引擎 LLM（兼容 OpenAI 协议） |
| `borax` | `borax.calendars` 生成中国农历日期 |
| `pyyaml` | 读取 YAML 配置 |
| `httpx` | 异步 HTTP 客户端（钉钉/飞书 Webhook 推送） |
| `python-dotenv` | 加载 `.env` 环境变量 |
| `fastapi` | Web UI 后端框架（async 原生，SSR + JSON API） |
| `uvicorn` | ASGI 服务器（运行 FastAPI 应用） |
| `jinja2` | 模板引擎（服务端渲染 HTML 页面） |
| `apscheduler` | 定时调度（CronTrigger，`--schedule` 模式） |
| `socksio` | SOCKS 代理支持（可选） |

## 添加新资讯源

编辑 `config/sources.yaml`，添加条目：
```yaml
- name: 来源名称
  url: https://example.com/news
  category: 分类标签
  enabled: true
```

## 注意事项

- 详细需求和 LLM Prompt 设计见 `docs/implementation-plan.md`
- Web UI 设计方案见 `docs/web-ui-design.md`
- 根目录 `main.py` 是占位文件，实际入口为 `src/main.py`
- 钉钉推送需配置环境变量：`D_ACCESS_TOKEN`、`D_SECRET`（见 `.env`）
- 飞书推送需配置环境变量：`FS_ACCESS_TOKEN`、`FS_SECRET`（见 `.env`）
- 无测试框架，当前不编写测试
- 代码注释使用中文，变量/函数名使用英文

# 📰 云雀简报（lark-brief）

每日资讯简报自动生成工具：**爬取多个资讯源 → LLM 精简总结 → 生成格式化简报 → 推送到钉钉/飞书**。

## ✨ 特性

- 🕷️ **智能爬取** — 基于 [crawl4ai](https://github.com/unclecode/crawl4ai) 三阶段爬取（批量→特殊源→重试），成功率 91%
- 🤖 **LLM 总结** — 火山引擎大模型并行提取摘要，兼容 OpenAI 协议，可灵活切换模型
- 📅 **农历日期** — 自动生成公历 + 农历日期（基于 borax）
- 🔀 **跨源去重** — LLM 语义去重、按重要性排序，精选 10-20 条；失败时自动降级为按重要度排序
- 📤 **多渠道推送** — 钉钉 & 飞书自定义机器人 Webhook 推送（HMAC-SHA256 加签），简报自动美化格式
- ⚠️ **智能告警** — 爬取全部失败或成功率低于阈值时，自动通过推送渠道发送告警
- 🌐 **Web UI** — 前后端分离架构：Next.js + HeroUI v3 现代化仪表盘，支持中英文双语切换与 Recharts 运行数据统计面板
- 💾 **同日覆盖** — 同一天重复运行时自动覆盖旧记录，每天只保留一条运行日志
- ⚙️ **配置驱动** — YAML 配置资讯源和参数，代码零硬编码，并支持为爬虫、LLM 和推送分别配置网络代理

## 📋 简报示例

```
今日简报

2026年3月24日，星期二，农历二月初六

1. OpenAI 发布 GPT-5 模型，推理能力大幅提升，支持 100 万 token 上下文。

2. GitHub 宣布 Copilot 全面免费开放给开源项目维护者。

...（共 10-20 条）
```

## 🚀 快速开始

### 环境要求

- Python ≥ 3.10
- [uv](https://docs.astral.sh/uv/) 包管理器

### 安装

```bash
git clone git@github.com:kurisu994/lark-brief.git
cd lark-brief
uv sync
```

### 配置

1. 复制 `.env.example` 为 `.env` 并填写：

```bash
# 火山引擎 LLM API Key
ARK_API_KEY=your-volcano-engine-api-key

# 钉钉机器人
D_SECRET=SECxxxxxx
D_ACCESS_TOKEN=xxxxxx

# 飞书机器人
FS_SECRET=xxxxxx
FS_ACCESS_TOKEN=xxxxxx
```

2. 根据需要编辑配置文件：

- `config/settings.yaml` — LLM 参数、爬虫配置、推送渠道
- `config/sources.yaml` — 资讯源列表

### 运行

```bash
# 单次生成简报
uv run python -m src.main

# 定时调度模式
uv run python -m src.main --schedule

# 启动后端 API
uv run lark-brief --web              # 默认端口 8080

# 启动前端开发服务器
cd frontend && pnpm dev              # 默认端口 3000

# Docker 一键部署（推荐）
docker compose up -d
```

生成的简报保存在 `output/YYYY-MM-DD.md`，同时推送到钉钉/飞书群。
Docker 部署后访问 `http://localhost:9090` 浏览 Web 界面。

## 🏗️ 项目结构

```
lark-brief/
├── config/
│   ├── settings.yaml       # 全局配置（LLM、爬虫、输出、推送）
│   └── sources.yaml        # 资讯源列表
├── src/                     # 后端（Python）
│   ├── pipeline.py          # 核心流程编排（爬取+总结+组装+推送）
│   ├── crawler.py           # 爬取模块
│   ├── summarizer.py        # LLM 总结模块
│   ├── composer.py          # 简报组装模块
│   ├── pusher.py            # 推送模块
│   ├── store.py             # SQLite 持久化
│   ├── main.py              # CLI 入口
│   └── web/                  # 纯 JSON API 模块
│       ├── __init__.py       # FastAPI app 工厂 + CORS
│       ├── routes.py         # RESTful API 路由
│       └── deps.py           # 依赖注入
├── frontend/                 # 前端（Next.js + HeroUI）
│   ├── app/                  # 页面路由
│   ├── components/           # 共享组件
│   ├── lib/api.ts            # API 服务层
│   ├── lib/i18n.tsx          # 国际化支持层
│   ├── Dockerfile            # 前端 Docker 镜像（Node Alpine）
│   └── public/favicon.ico    # 站点图标
├── output/                   # 简报输出目录
├── data/                     # SQLite 数据库
├── Dockerfile                # 后端 Docker 镜像
└── docker-compose.yml        # 三服务编排
```

## 📡 当前资讯源（23 个）

| 板块 | 来源 |
|------|------|
| 开发技术 | InfoQ 中文、Hacker News、GitHub Blog Engineering |
| AI/开源 | Hugging Face Blog、VentureBeat AI |
| 商业科技 | 36氪快讯、虎嗅、雷峰网、IT之家 |
| 海外科技 | TechCrunch、The Verge、Ars Technica、Reuters |
| 时政/综合 | 新华网、央视新闻、澎湃新闻、中国新闻网 |
| 国际 | BBC World、AP News、Al Jazeera、The Guardian |
| 政策 | 工信部、国家网信办 |

添加新源只需编辑 `config/sources.yaml`。

## 🗺️ 路线图

**规划中：**

- [ ] 📡 RSS/Atom 订阅源支持 — 除网页爬取外，直接解析 RSS Feed
- [ ] 📧 邮件推送 — 支持 SMTP 发送简报邮件（HTML 格式）
- [ ] 💬 企业微信推送 — 企微机器人 Webhook 推送
- [ ] 📄 简报 PDF 导出 — Web UI 支持一键导出精排版 PDF
- [ ] 🔐 Web UI 认证 — 基于 Token 或密码的访问控制
- [ ] 🔌 多 LLM 提供商 — 支持 OpenAI / Anthropic / 本地模型等多后端切换
- [ ] 🚫 资讯源自动熔断 — 连续失败 N 天的源自动禁用并通知
- [ ] 📊 Prometheus 指标 — 暴露爬取成功率、耗时等监控指标
- [ ] 🏷️ 自定义分类标签 — Web UI 按分类筛选和浏览简报
- [ ] 🔔 Telegram / Discord 推送 — 支持更多 IM 推送渠道

<details>
<summary>✅ 已完成</summary>

- [x] 核心流程：爬取 → 总结 → 组装 → 保存
- [x] 钉钉 & 飞书机器人推送（HMAC 加签 + 美化格式）
- [x] LLM 提取并行化（asyncio.gather）+ 降级容错
- [x] 爬取稳定性优化（三阶段爬取 + 重试 + 超时配置）
- [x] 爬取成功率告警 + 同日覆盖
- [x] 新增代理配置、拆分执行管线 (pipeline.py)
- [x] cron 定时调度 + Docker 部署
- [x] Web UI — 简报列表 / 详情 / 统计图表 (Recharts) / 源健康度
- [x] Web UI — 手动生成 / 全文搜索 / 国际化 (i18n)
- [x] 前后端分离 — Next.js + HeroUI v3 前端 + FastAPI 纯 API 后端

</details>

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

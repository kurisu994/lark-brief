# 📰 云雀简报（lark-brief）

每日资讯简报自动生成工具：**爬取多个资讯源 → LLM 精简总结 → 生成格式化简报 → 推送到钉钉/飞书**。

## ✨ 特性

- 🕷️ **智能爬取** — 基于 [crawl4ai](https://github.com/unclecode/crawl4ai) 三阶段爬取（批量→特殊源→重试），成功率 91%
- 🤖 **LLM 总结** — 火山引擎大模型并行提取摘要，兼容 OpenAI 协议，可灵活切换模型
- 📅 **农历日期** — 自动生成公历 + 农历日期（基于 borax）
- 🔀 **跨源去重** — LLM 语义去重、按重要性排序，精选 10-20 条
- 📤 **多渠道推送** — 钉钉 & 飞书自定义机器人 Webhook 推送（HMAC-SHA256 加签）
- 🌐 **Web UI** — 轻量级 Web 界面，浏览历史简报和运行统计（FastAPI + Tailwind，欧美极简风格，支持 Dark Mode）
- ⚙️ **配置驱动** — YAML 配置资讯源和参数，代码零硬编码

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

# 启动 Web UI
uv run lark-brief --web              # 默认端口 8080
uv run lark-brief --web --port 3000  # 自定义端口
```

生成的简报保存在 `output/YYYY-MM-DD.md`，同时推送到钉钉/飞书群。
Web UI 访问 `http://localhost:8080` 浏览历史简报。

## 🏗️ 项目结构

```
lark-brief/
├── config/
│   ├── settings.yaml       # 全局配置（LLM、爬虫、输出、推送）
│   └── sources.yaml        # 资讯源列表
├── src/
│   ├── crawler.py           # 爬取模块：crawl4ai 并发爬取 + 内容过滤
│   ├── summarizer.py        # 总结模块：LLM 摘要提取 + 去重排序
│   ├── composer.py          # 组装模块：简报格式化（含农历日期）
│   ├── pusher.py            # 推送模块：钉钉 & 飞书机器人 Webhook
│   ├── store.py             # 持久化模块：SQLite 运行日志
│   ├── main.py              # 入口：串联完整流程 + CLI
│   └── web/                  # Web UI 模块
│       ├── __init__.py       # FastAPI app 工厂
│       ├── routes.py         # 页面路由 + API 路由
│       ├── deps.py           # 依赖注入
│       ├── static/           # 自定义样式
│       └── templates/        # Jinja2 模板（欧美极简风格）
├── output/                   # 简报输出目录
├── data/                     # SQLite 数据库
└── docs/                     # 设计文档
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

- [x] 核心流程：爬取 → 总结 → 组装 → 保存
- [x] 钉钉机器人推送
- [x] 飞书机器人推送
- [x] LLM 提取并行化（asyncio.gather）
- [x] 爬取稳定性优化（重试 + 超时配置）
- [x] cron 定时调度
- [x] Docker 部署
- [x] Web UI — 简报列表 + 详情页 + Dark Mode（Phase 1）
- [ ] Web UI — 统计面板 + 源健康度（Phase 2）

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

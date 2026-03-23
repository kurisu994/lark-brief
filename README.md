# 📰 云雀简报（lark-brief）

每日资讯简报自动生成工具：**定时爬取多个资讯源 → LLM 精简总结 → 生成格式化简报 Markdown 文件**。

## ✨ 特性

- 🕷️ **智能爬取** — 基于 [crawl4ai](https://github.com/unclecode/crawl4ai) 异步并发爬取，`PruningContentFilter` 自动去噪
- 🤖 **LLM 总结** — 火山引擎大模型提取摘要，兼容 OpenAI 协议，可灵活切换模型
- 📅 **农历日期** — 自动生成公历 + 农历日期（基于 borax）
- 🔀 **跨源去重** — 多源新闻智能去重、按重要性排序，精选 10-15 条
- ⚙️ **配置驱动** — YAML 配置资讯源和参数，代码零硬编码

## 📋 简报示例

```
今日简报

2026年3月23日，星期一，农历三月初五

1. OpenAI 发布 GPT-5 模型，推理能力大幅提升，支持 100 万 token 上下文。
   🔗 https://openai.com/news/gpt-5

2. GitHub 宣布 Copilot 全面免费开放给开源项目维护者。
   🔗 https://github.blog/engineering/copilot-free-oss

...（共 10-15 条）
```

## 🚀 快速开始

### 环境要求

- Python ≥ 3.10
- [uv](https://docs.astral.sh/uv/) 包管理器
- 火山引擎 API Key

### 安装

```bash
git clone git@github.com:kurisu994/lark-brief.git
cd lark-brief
uv sync
```

### 配置

1. 设置环境变量：

```bash
export ARK_API_KEY="your-volcano-engine-api-key"
```

2. 根据需要编辑配置文件：

- `config/settings.yaml` — LLM 端点、爬虫参数、输出路径
- `config/sources.yaml` — 资讯源列表

### 运行

```bash
uv run python -m src.main
# 或
uv run lark-brief
```

生成的简报将保存在 `output/YYYY-MM-DD.md`。

## 🏗️ 项目结构

```
lark-brief/
├── config/
│   ├── settings.yaml      # 全局配置（LLM、爬虫、输出）
│   └── sources.yaml       # 资讯源列表
├── src/
│   ├── crawler.py          # 爬取模块
│   ├── summarizer.py       # LLM 总结模块
│   ├── composer.py         # 简报组装模块
│   └── main.py             # 入口，串联完整流程
├── output/                  # 简报输出目录
└── docs/                    # 设计文档
```

## 📡 当前资讯源

| 来源 | 板块 |
|------|------|
| InfoQ 中文 | 开发技术 |
| Hacker News | 全球开发者 |
| Hugging Face Blog | AI/开源 |
| GitHub Blog Engineering | 工程工具链 |
| 36氪快讯 | 商业科技 |
| Reuters Technology | 海外科技 |

添加新源只需编辑 `config/sources.yaml`。

## 🗺️ 路线图

- [ ] 飞书 Webhook 推送
- [ ] cron 定时调度
- [ ] 错误告警与日志
- [ ] 更多资讯源接入
- [ ] Docker 部署

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

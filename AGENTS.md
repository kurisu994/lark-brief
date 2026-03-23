# AGENTS.md — lark-brief

## 项目概述

每日资讯简报自动生成工具，三阶段管线：**爬取 → LLM 总结 → 格式化简报 MD**。

## 架构

```
src/main.py          # 入口，串联完整异步流程 (asyncio)
src/crawler.py       # 爬取模块 — crawl4ai 并发爬取 + PruningContentFilter 去噪
src/summarizer.py    # 总结模块 — 火山引擎 LLM 提取摘要 + 跨源去重排序
src/composer.py      # 组装模块 — 格式化简报 MD（含 borax 农历日期）
config/settings.yaml # 全局配置：LLM 端点、爬虫参数、输出路径、条目数量
config/sources.yaml  # 资讯源列表：name/url/category/enabled
output/              # 生成的简报归档，格式 YYYY-MM-DD.md
```

**数据流**: `sources.yaml → crawler(CrawlResult) → summarizer(NewsItem) → composer(str) → output/*.md`

## 关键约定

- **异步优先**: 爬取和 LLM 调用均为 `async`，入口通过 `asyncio.run()` 驱动
- **数据类传递**: 模块间通过 `dataclass` 传递数据（`CrawlResult`、`NewsItem`），不使用裸 dict
- **LLM 协议**: 使用 `openai` SDK 连接火山引擎（只替换 `base_url`），API Key 通过环境变量 `ARK_API_KEY` 读取
- **配置与代码分离**: 所有可变参数放 YAML，代码中不硬编码资讯源或模型 ID
- **简报格式固定**: 输出格式见 `docs/implementation-plan.md` §二，编号列表 + 🔗链接，全中文，10-15 条

## 开发环境

```bash
# 依赖管理使用 uv（非 pip），锁文件为 uv.lock
uv sync                    # 安装依赖
uv run python -m src.main  # 运行（或 uv run lark-brief）

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
| `httpx` | 异步 HTTP 客户端（预留飞书推送） |

## 添加新资讯源

编辑 `config/sources.yaml`，添加条目：
```yaml
- name: 来源名称
  url: https://example.com/news
  category: 分类标签
  enabled: true
```

## 注意事项

- 项目当前处于 **MVP 骨架阶段**，核心函数均为 `TODO + raise NotImplementedError`
- 详细需求和 LLM Prompt 设计见 `docs/implementation-plan.md`
- 根目录 `main.py` 是占位文件，实际入口为 `src/main.py`
- 无测试框架，当前不编写测试
- 代码注释使用中文，变量/函数名使用英文

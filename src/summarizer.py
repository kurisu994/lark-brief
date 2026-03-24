"""总结模块：调用火山引擎 LLM 提取新闻摘要，跨源去重排序"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# 单源提取 Prompt 模板
EXTRACT_PROMPT = """你是一位资深的科技资讯编辑。请从以下资讯内容中提取最重要、最有价值的新闻。

要求：
1. 每条新闻用 1-2 句中文概括核心信息
2. 保留原文链接
3. 海外资讯翻译为中文
4. 只提取今天或近期的新闻，忽略过时内容
5. 严格返回 JSON 格式，不要包含其他内容

输出格式：
[
  {{
    "summary": "新闻摘要",
    "url": "原文链接",
    "importance": 8
  }}
]

以下是来自「{source_name}」（{category}）的资讯内容：
{content}"""

# 合并去重排序 Prompt 模板
MERGE_PROMPT = """你是一位面向软件工程师的资讯编辑。以下是从多个来源提取的新闻列表，请进行去重和排序：

要求：
1. 识别重复或高度相似的新闻（同一事件的不同报道），合并为一条，保留信息量更大的版本
2. 按重要性和时效性排序
3. 最终选取 {min_items}-{max_items} 条最有价值的新闻
4. 软件工程师相关板块（开发技术、AI、开源、安全）的新闻总占比控制在 40% 左右
5. 保持每条新闻的摘要和链接不变
6. 严格返回 JSON 数组，不要包含其他内容

{all_news_json}"""


@dataclass
class NewsItem:
    """单条新闻"""

    summary: str
    url: str
    importance: int


def _create_client(settings: dict) -> AsyncOpenAI:
    """创建火山引擎 LLM 客户端"""
    return AsyncOpenAI(
        api_key=os.environ.get("ARK_API_KEY", ""),
        base_url=settings.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"),
        timeout=settings.get("query_timeout", 120),
    )


def _parse_news_json(text: str) -> list[dict[str, Any]]:
    """从 LLM 响应中解析 JSON 数组

    处理可能被 markdown 代码块包裹的 JSON。
    """
    text = text.strip()
    # 去除 markdown 代码块标记
    if text.startswith("```"):
        lines = text.split("\n")
        # 去掉首尾的 ``` 行
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


async def extract_news(
    source_name: str,
    category: str,
    markdown: str,
    settings: dict,
) -> list[NewsItem]:
    """从单个资讯源的内容中提取新闻摘要

    Args:
        source_name: 资讯源名称
        category: 资讯分类
        markdown: 爬取到的 markdown 内容
        settings: LLM 配置（来自 settings.yaml 的 llm 节）
    """
    client = _create_client(settings)
    prompt = EXTRACT_PROMPT.format(
        source_name=source_name,
        category=category,
        content=markdown,
    )

    try:
        response = await client.chat.completions.create(
            model=settings["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.get("temperature", 0.7),
            top_p=settings.get("top_p", 0.95),
            max_tokens=settings.get("max_tokens", 4096),
        )
        content = response.choices[0].message.content or ""
        items = _parse_news_json(content)
        result = [
            NewsItem(
                summary=item.get("summary", ""),
                url=item.get("url", ""),
                importance=int(item.get("importance", 5)),
            )
            for item in items
            if item.get("summary")
        ]
        logger.info("✅ 从「%s」提取到 %d 条新闻", source_name, len(result))
        return result
    except Exception as e:
        logger.warning("❌ 从「%s」提取新闻失败: %s", source_name, e)
        return []


async def merge_and_rank(
    all_news: list[NewsItem],
    settings: dict,
    max_items: int = 15,
    min_items: int = 10,
) -> list[NewsItem]:
    """跨源去重、按重要性排序，选取指定数量的新闻

    Args:
        all_news: 所有源提取的新闻列表
        settings: LLM 配置
        max_items: 最大条目数
        min_items: 最小条目数
    """
    if not all_news:
        return []

    # 条目数不多时直接排序返回，无需 LLM 去重
    if len(all_news) <= max_items:
        logger.info("新闻总数 (%d) 不超过上限 (%d)，跳过 LLM 去重", len(all_news), max_items)
        return sorted(all_news, key=lambda x: x.importance, reverse=True)

    client = _create_client(settings)
    all_news_json = json.dumps(
        [asdict(item) for item in all_news],
        ensure_ascii=False,
        indent=2,
    )
    prompt = MERGE_PROMPT.format(
        min_items=min_items,
        max_items=max_items,
        all_news_json=all_news_json,
    )

    try:
        response = await client.chat.completions.create(
            model=settings["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=settings.get("temperature", 0.7),
            top_p=settings.get("top_p", 0.95),
            max_tokens=settings.get("max_tokens", 4096),
        )
        content = response.choices[0].message.content or ""
        items = _parse_news_json(content)
        result = [
            NewsItem(
                summary=item.get("summary", ""),
                url=item.get("url", ""),
                importance=int(item.get("importance", 5)),
            )
            for item in items
            if item.get("summary")
        ]
        logger.info("✅ 去重排序后剩余 %d 条新闻", len(result))
        return result
    except Exception as e:
        # 降级：直接按 importance 排序取 Top N
        logger.warning("❌ LLM 去重排序失败，降级为按重要性排序: %s", e)
        sorted_news = sorted(all_news, key=lambda x: x.importance, reverse=True)
        return sorted_news[:max_items]

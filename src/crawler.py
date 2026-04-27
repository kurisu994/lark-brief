"""爬取模块：调用 crawl4ai 并发爬取资讯源，使用内容过滤去噪"""

import logging
import random
from collections import defaultdict
from dataclasses import dataclass

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai import CrawlResult as RawCrawlResult
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """单个资讯源的爬取结果"""

    source_name: str
    category: str
    url: str
    markdown: str
    success: bool
    error: str | None = None


def _make_crawler_config(
    filter_threshold: float,
    page_timeout: int,
    wait_for: str | None = None,
) -> CrawlerRunConfig:
    """构建爬虫运行配置"""
    return CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=filter_threshold)
        ),
        page_timeout=page_timeout,
        wait_for=wait_for,
    )


def _extract_content(raw: RawCrawlResult, source: dict) -> CrawlResult:
    """从 crawl4ai 原始结果中提取内容，返回统一的 CrawlResult"""
    name = source["name"]
    category = source.get("category", "")
    url = source["url"]

    try:
        if raw.success and raw.markdown:
            md_result = raw.markdown
            content = md_result.fit_markdown or md_result.raw_markdown or ""
            if content:
                return CrawlResult(
                    source_name=name, category=category,
                    url=url, markdown=content, success=True,
                )
        error_msg = getattr(raw, "error_message", None) or "内容为空"
        return CrawlResult(
            source_name=name, category=category,
            url=url, markdown="", success=False, error=error_msg,
        )
    except Exception as e:
        return CrawlResult(
            source_name=name, category=category,
            url=url, markdown="", success=False, error=str(e),
        )


def _category_weight(category: str, category_weights: dict[str, float] | None) -> float:
    """读取分类权重，非法或负数权重按 0 处理"""
    if not category_weights:
        return 1.0
    try:
        return max(float(category_weights.get(category, 1.0)), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _weighted_sample_without_replacement(
    items: list[dict],
    count: int,
    category_weights: dict[str, float] | None,
) -> list[dict]:
    """按分类权重无重复抽样"""
    pool = items.copy()
    selected: list[dict] = []

    while pool and len(selected) < count:
        weights = [_category_weight(s.get("category", "未分类"), category_weights) for s in pool]
        if sum(weights) <= 0:
            break
        chosen = random.choices(pool, weights=weights, k=1)[0]
        selected.append(chosen)
        pool.remove(chosen)

    return selected


def select_sources(
    sources: list[dict],
    select_count: int = 0,
    category_weights: dict[str, float] | None = None,
) -> list[dict]:
    """按分类权重随机选取资讯源

    Args:
        sources: 所有启用的资讯源列表
        select_count: 选取数量，0 表示全部选取
        category_weights: 分类抽样权重，未配置分类默认为 1.0

    Returns:
        选中的资讯源列表
    """
    enabled = [s for s in sources if s.get("enabled", True)]
    if select_count <= 0 or select_count >= len(enabled):
        return enabled

    if category_weights:
        pool = [
            s
            for s in enabled
            if _category_weight(s.get("category", "未分类"), category_weights) > 0
        ]
        selected = _weighted_sample_without_replacement(
            pool,
            min(select_count, len(pool)),
            category_weights,
        )
        random.shuffle(selected)
        logger.info(
            "加权选源: 从 %d 个源中选取 %d 个，覆盖 %d 个分类",
            len(enabled), len(selected),
            len({s.get("category") for s in selected}),
        )
        return selected

    # 按 category 分组
    by_category: dict[str, list[dict]] = defaultdict(list)
    for s in enabled:
        by_category[s.get("category", "未分类")].append(s)

    categories = list(by_category.keys())
    selected_categories = categories[:select_count] if len(categories) <= select_count else random.sample(categories, select_count)

    selected = [random.choice(by_category[cat]) for cat in selected_categories]

    remaining = select_count - len(selected)
    if remaining > 0:
        selected_set = {id(s) for s in selected}
        pool = [s for s in enabled if id(s) not in selected_set]
        if pool:
            extra = random.sample(pool, min(remaining, len(pool)))
            selected.extend(extra)

    random.shuffle(selected)
    logger.info(
        "选源: 从 %d 个源中选取 %d 个，覆盖 %d 个分类",
        len(enabled), len(selected),
        len({s.get("category") for s in selected}),
    )
    return selected


async def crawl_sources(
    sources: list[dict],
    headless: bool = True,
    filter_threshold: float = 0.45,
    page_timeout: int = 60000,
    retry_count: int = 0,
    proxy: str | None = None,
) -> list[CrawlResult]:
    """并发爬取所有启用的资讯源，返回爬取结果列表

    Args:
        sources: 资讯源配置列表（来自 sources.yaml）
        headless: 是否使用无头浏览器模式
        filter_threshold: PruningContentFilter 去噪阈值
        page_timeout: 页面加载超时（毫秒）
        retry_count: 失败源的重试次数
        proxy: 代理地址（例如 'socks5://127.0.0.1:1080'）
    """
    enabled = [s for s in sources if s.get("enabled", True)]
    if not enabled:
        logger.warning("没有启用的资讯源")
        return []

    # 区分需要特殊配置（wait_for）的源和普通源
    normal_sources = [s for s in enabled if not s.get("wait_for")]
    special_sources = [s for s in enabled if s.get("wait_for")]

    logger.info("开始爬取 %d 个资讯源: %s", len(enabled), [s["name"] for s in enabled])

    browser_config = BrowserConfig(headless=headless, proxy=proxy)
    default_config = _make_crawler_config(filter_threshold, page_timeout)

    results: list[CrawlResult] = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        # --- 第一阶段：批量爬取普通源 ---
        if normal_sources:
            normal_urls = [s["url"] for s in normal_sources]
            raw_results = await crawler.arun_many(
                urls=normal_urls, config=default_config,
            )
            # URL → 爬取结果映射（arun_many 返回顺序可能与输入不一致）
            result_map = {r.url: r for r in raw_results}

            for source in normal_sources:
                raw = result_map.get(source["url"])
                if raw is None:
                    results.append(CrawlResult(
                        source_name=source["name"],
                        category=source.get("category", ""),
                        url=source["url"], markdown="",
                        success=False, error="未收到爬取结果",
                    ))
                    logger.warning("❌ 爬取失败: %s — 未收到爬取结果", source["name"])
                else:
                    results.append(_extract_content(raw, source))

        # --- 第二阶段：单独爬取需要特殊配置的源（如 SPA wait_for） ---
        for source in special_sources:
            special_config = _make_crawler_config(
                filter_threshold, page_timeout, wait_for=source["wait_for"],
            )
            raw = await crawler.arun(url=source["url"], config=special_config)
            results.append(_extract_content(raw, source))

        # 记录首轮结果
        for r in results:
            if r.success:
                logger.info("✅ 爬取成功: %s (%d 字符)", r.source_name, len(r.markdown))
            else:
                logger.warning("❌ 爬取失败: %s — %s", r.source_name, r.error)

        # --- 第三阶段：重试失败的源 ---
        if retry_count > 0:
            failed = [(i, r) for i, r in enumerate(results) if not r.success]
            if failed:
                logger.info("🔄 开始重试 %d 个失败源（最多 %d 次）", len(failed), retry_count)
                source_by_url = {s["url"]: s for s in enabled}

                for attempt in range(1, retry_count + 1):
                    still_failed: list[tuple[int, CrawlResult]] = []
                    for idx, fail_result in failed:
                        source_cfg = source_by_url.get(fail_result.url)
                        if not source_cfg:
                            continue
                        retry_config = _make_crawler_config(
                            filter_threshold, page_timeout,
                            wait_for=source_cfg.get("wait_for"),
                        )
                        raw = await crawler.arun(
                            url=fail_result.url, config=retry_config,
                        )
                        new_result = _extract_content(raw, source_cfg)
                        if new_result.success:
                            results[idx] = new_result
                            logger.info(
                                "✅ 重试成功 (第%d次): %s (%d 字符)",
                                attempt, new_result.source_name, len(new_result.markdown),
                            )
                        else:
                            still_failed.append((idx, fail_result))
                    failed = still_failed
                    if not failed:
                        break

    success_count = sum(1 for r in results if r.success)
    logger.info("爬取完成: %d/%d 成功", success_count, len(results))
    return results

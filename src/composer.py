"""组装模块：将新闻列表格式化为简报 MD，包含公历+农历日期"""

from src.summarizer import NewsItem


def compose_brief(news_items: list[NewsItem]) -> str:
    """将新闻列表组装为简报 Markdown 文本"""
    # TODO: 实现简报组装逻辑
    raise NotImplementedError


def get_date_line() -> str:
    """生成日期行：公历日期 + 星期 + 农历日期"""
    # TODO: 实现日期格式化（含 borax 农历）
    raise NotImplementedError

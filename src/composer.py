"""组装模块：将新闻列表格式化为简报 MD，包含公历+农历日期"""

from datetime import date

from borax.calendars.lunardate import LunarDate

from src.summarizer import NewsItem

# 星期映射
_WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]


def get_date_line(today: date | None = None) -> str:
    """生成日期行：公历日期 + 星期 + 农历日期

    示例输出：2026年3月23日，星期一，农历三月初五
    """
    if today is None:
        today = date.today()

    weekday = _WEEKDAY_NAMES[today.weekday()]
    lunar = LunarDate.from_solar(today)
    # 仅取月+日，如「农历二月初五」
    lunar_str = f"农历{lunar.cn_month}月{lunar.cn_day}"

    return f"{today.year}年{today.month}月{today.day}日，星期{weekday}，{lunar_str}"


def compose_brief(news_items: list[NewsItem], today: date | None = None) -> str:
    """将新闻列表组装为简报 Markdown 文本

    Args:
        news_items: 去重排序后的新闻列表
        today: 指定日期（默认为当天）
    """
    date_line = get_date_line(today)

    lines = ["今日简报", "", date_line, ""]

    for i, item in enumerate(news_items, 1):
        lines.append(f"{i}. {item.summary}")
        lines.append(f"   🔗 {item.url}")
        lines.append("")

    return "\n".join(lines)

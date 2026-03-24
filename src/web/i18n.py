"""国际化模块：支持中英文界面切换

通过 contextvars 实现请求级别的语言隔离，
翻译文件为 JSON 格式存放在 locales/ 目录下。
"""

import json
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fastapi import Request, Response

# 支持的语言列表
SUPPORTED_LOCALES = ("en", "zh")
DEFAULT_LOCALE = "en"

# HTML lang 属性映射
_HTML_LANG_MAP: dict[str, str] = {"en": "en", "zh": "zh-CN"}

# 当前请求的语言（contextvars 保证协程安全）
_current_locale: ContextVar[str] = ContextVar("locale", default=DEFAULT_LOCALE)

# 翻译数据缓存：{locale: {key: text}}
_translations: dict[str, dict[str, str]] = {}


def load_translations() -> None:
    """从 locales/ 目录加载所有语言的翻译文件"""
    locales_dir = Path(__file__).resolve().parent / "locales"
    for locale in SUPPORTED_LOCALES:
        filepath = locales_dir / f"{locale}.json"
        if filepath.exists():
            _translations[locale] = json.loads(filepath.read_text("utf-8"))


def t(key: str, **kwargs: Any) -> str:
    """翻译函数：根据当前语言返回对应文本

    Args:
        key: 翻译键名
        **kwargs: 格式化参数（如 count、days 等）
    """
    locale = _current_locale.get()
    text = _translations.get(locale, {}).get(key)
    if text is None:
        # 回退到默认语言，仍未找到则返回键名本身
        text = _translations.get(DEFAULT_LOCALE, {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def get_locale() -> str:
    """获取当前请求的语言代码"""
    return _current_locale.get()


def get_html_lang() -> str:
    """获取当前语言对应的 HTML lang 属性值"""
    return _HTML_LANG_MAP.get(_current_locale.get(), "en")


def set_locale(locale: str) -> None:
    """设置当前请求的语言"""
    if locale in SUPPORTED_LOCALES:
        _current_locale.set(locale)
    else:
        _current_locale.set(DEFAULT_LOCALE)


def detect_locale(cookie_lang: str | None, accept_language: str | None) -> str:
    """检测用户语言偏好

    优先级：Cookie > Accept-Language 请求头 > 默认值
    """
    if cookie_lang and cookie_lang in SUPPORTED_LOCALES:
        return cookie_lang

    if accept_language:
        for part in accept_language.split(","):
            lang = part.split(";")[0].strip().lower()
            if lang.startswith("zh"):
                return "zh"
            if lang.startswith("en"):
                return "en"

    return DEFAULT_LOCALE


def create_i18n_middleware() -> Callable[..., Any]:
    """创建国际化中间件：在每个请求前检测并设置语言"""

    async def i18n_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        cookie_lang = request.cookies.get("lang")
        accept_lang = request.headers.get("accept-language")
        locale = detect_locale(cookie_lang, accept_lang)
        set_locale(locale)
        return await call_next(request)

    return i18n_middleware

"use client";

import { createContext, useContext, useState, useCallback, useEffect } from "react";

/** 支持的语言列表 */
export type Locale = "zh" | "en";

/** 翻译数据 */
const translations: Record<Locale, Record<string, string>> = {
  zh: {
    // 导航
    "nav.home": "首页",
    "nav.stats": "统计",
    "nav.search": "搜索",
    "nav.subtitle": "每日资讯简报",
    // 首页
    "home.title": "每日资讯简报",
    "home.total": "共 {total} 期简报归档",
    "home.generate": "✨ 生成简报",
    "home.generating": "生成中...",
    "home.empty": "暂无简报记录，请点击「生成简报」开始",
    "home.news_count": "📰 {count} 条新闻",
    "home.source_count": "✅ {success}/{total} 源",
    "home.duration": "⏱ {sec}s",
    "home.prev": "上一页",
    "home.next": "下一页",
    "home.kpi_total": "总期数",
    "home.kpi_latest": "最新日期",
    "home.kpi_news": "最新新闻数",
    "home.kpi_rate": "最新成功率",
    "home.col_date": "日期",
    "home.col_status": "状态",
    "home.col_news": "新闻数",
    "home.col_sources": "成功源",
    "home.col_duration": "耗时",
    // 状态
    "status.success": "成功",
    "status.running": "运行中",
    "status.failed": "失败",
    // 详情页
    "detail.breadcrumb_home": "首页",
    "detail.brief_title": "{date} 简报",
    "detail.no_content": "暂无简报内容",
    "detail.not_found": "未找到 {date} 的简报记录",
    "detail.back": "← 返回首页",
    "detail.run_info": "运行信息",
    "detail.status": "状态",
    "detail.news_count": "新闻数",
    "detail.success_sources": "成功源",
    "detail.duration": "耗时",
    "detail.source_detail": "爬取源详情",
    "detail.read_more": "阅读原文",
    // 统计页
    "stats.title": "运行统计",
    "stats.total_runs": "总运行次数",
    "stats.avg_rate": "平均成功率",
    "stats.avg_duration": "平均耗时",
    "stats.avg_news": "平均新闻数",
    "stats.trend_title": "近 30 天趋势",
    "stats.col_date": "日期",
    "stats.col_rate": "成功率",
    "stats.col_news": "新闻数",
    "stats.col_duration": "耗时",
    "stats.col_sources": "源数",
    "stats.health_title": "源健康度（近 7 天）",
    "stats.col_name": "源名称",
    "stats.col_total": "总次数",
    "stats.col_recent": "近期状态",
    "stats.news_trend": "新闻数趋势",
    "stats.rate_trend": "成功率趋势",
    "stats.last_n_days": "近 {n} 天",
    "stats.rate_label": "成功率",
    // 搜索页
    "search.title": "全文搜索",
    "search.placeholder": "输入关键词搜索历史简报...",
    "search.result_count": "找到 {total} 条与「{query}」相关的结果",
    "search.match_count": "{count} 处匹配",
    "search.no_result": "未找到与「{query}」相关的信息",
  },
  en: {
    // 导航
    "nav.home": "Home",
    "nav.stats": "Stats",
    "nav.search": "Search",
    "nav.subtitle": "Daily News Brief",
    // 首页
    "home.title": "Daily News Brief",
    "home.total": "{total} briefs archived",
    "home.generate": "✨ Generate",
    "home.generating": "Generating...",
    "home.empty": "No briefs yet. Click \"Generate\" to start.",
    "home.news_count": "📰 {count} news",
    "home.source_count": "✅ {success}/{total} sources",
    "home.duration": "⏱ {sec}s",
    "home.prev": "Previous",
    "home.next": "Next",
    "home.kpi_total": "Total Briefs",
    "home.kpi_latest": "Latest Date",
    "home.kpi_news": "Latest News",
    "home.kpi_rate": "Latest Rate",
    "home.col_date": "Date",
    "home.col_status": "Status",
    "home.col_news": "News",
    "home.col_sources": "Sources",
    "home.col_duration": "Duration",
    // 状态
    "status.success": "Success",
    "status.running": "Running",
    "status.failed": "Failed",
    // 详情页
    "detail.breadcrumb_home": "Home",
    "detail.brief_title": "Brief — {date}",
    "detail.no_content": "No content available",
    "detail.not_found": "No brief found for {date}",
    "detail.back": "← Back to Home",
    "detail.run_info": "Run Info",
    "detail.status": "Status",
    "detail.news_count": "News",
    "detail.success_sources": "Sources",
    "detail.duration": "Duration",
    "detail.source_detail": "Source Details",
    "detail.read_more": "Read Source",
    // 统计页
    "stats.title": "Statistics",
    "stats.total_runs": "Total Runs",
    "stats.avg_rate": "Avg Success Rate",
    "stats.avg_duration": "Avg Duration",
    "stats.avg_news": "Avg News",
    "stats.trend_title": "Last 30 Days Trend",
    "stats.col_date": "Date",
    "stats.col_rate": "Success Rate",
    "stats.col_news": "News",
    "stats.col_duration": "Duration",
    "stats.col_sources": "Sources",
    "stats.health_title": "Source Health (Last 7 Days)",
    "stats.col_name": "Source Name",
    "stats.col_total": "Total",
    "stats.col_recent": "Recent",
    "stats.news_trend": "News Count Trend",
    "stats.rate_trend": "Success Rate Trend",
    "stats.last_n_days": "Last {n} days",
    "stats.rate_label": "Success Rate",
    // 搜索页
    "search.title": "Full-text Search",
    "search.placeholder": "Search briefs by keyword...",
    "search.result_count": "Found {total} results for \"{query}\"",
    "search.match_count": "{count} matches",
    "search.no_result": "No results found for \"{query}\"",
  },
};

interface I18nContextType {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

/** 国际化 Provider */
export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh");

  // 初始化时从 localStorage 读取
  useEffect(() => {
    const saved = localStorage.getItem("locale") as Locale | null;
    if (saved && (saved === "zh" || saved === "en")) {
      setLocaleState(saved);
    }
  }, []);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem("locale", newLocale);
    document.documentElement.lang = newLocale === "zh" ? "zh-CN" : "en";
  }, []);

  /** 翻译函数，支持 {key} 参数替换 */
  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => {
      let text = translations[locale]?.[key] ?? translations.zh[key] ?? key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          text = text.replace(`{${k}}`, String(v));
        });
      }
      return text;
    },
    [locale]
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

/** 使用国际化的 Hook */
export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/lib/i18n";
import {
  BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  fetchStatsOverview,
  fetchStatsTrend,
  fetchSourcesHealth,
  type StatsOverview,
  type TrendItem,
  type SourceHealth,
} from "@/lib/api";

/** 统计面板页（KPI + 图表 + 表格） */
export default function StatsPage() {
  const { t } = useI18n();
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [trend, setTrend] = useState<TrendItem[]>([]);
  const [sources, setSources] = useState<SourceHealth[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchStatsOverview(),
      fetchStatsTrend(30),
      fetchSourcesHealth(7),
    ])
      .then(([ov, tr, sr]) => {
        setOverview(ov);
        setTrend(tr.data);
        setSources(sr.data);
      })
      .catch((e) => console.error("加载统计数据失败:", e))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-6 h-6 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  // 图表数据：截取短日期
  const chartData = trend.map((item) => ({
    ...item,
    date: item.run_date.slice(5), // "03-25"
    rate: Math.round(item.success_rate * 100),
  }));

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{t("stats.title")}</h1>

      {/* KPI 卡片行 */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card-sm">
            <div className="kpi-label">{t("stats.total_runs")}</div>
            <div className="kpi-value">{overview.total_runs}</div>
          </div>
          <div className="card-sm">
            <div className="kpi-label">{t("stats.avg_rate")}</div>
            <div className="flex items-baseline gap-2">
              <span className="kpi-value">{(overview.avg_success_rate * 100).toFixed(0)}%</span>
              <span className={`kpi-change ${overview.avg_success_rate >= 0.8 ? "kpi-change-up" : "kpi-change-down"}`}>
                {overview.avg_success_rate >= 0.8 ? "↑" : "↓"} {(overview.avg_success_rate * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          <div className="card-sm">
            <div className="kpi-label">{t("stats.avg_duration")}</div>
            <div className="kpi-value">{overview.avg_duration_sec.toFixed(0)}s</div>
          </div>
          <div className="card-sm">
            <div className="kpi-label">{t("stats.avg_news")}</div>
            <div className="kpi-value">{overview.avg_news_count.toFixed(0)}</div>
          </div>
        </div>
      )}

      {/* 图表行 */}
      {chartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 新闻数柱状图 */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{t("stats.news_trend")}</h3>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{t("stats.last_n_days", { n: chartData.length })}</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData} barSize={16}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={Math.floor(chartData.length / 6)} />
                <YAxis tick={{ fontSize: 11 }} width={30} />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '0.5rem', fontSize: '0.8rem' }}
                  labelStyle={{ color: 'var(--text-muted)' }}
                  itemStyle={{ color: '#a78bfa' }}
                />
                <Bar dataKey="news_count" fill="#7c3aed" radius={[4, 4, 0, 0]} name={t("stats.col_news")} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* 成功率折线图 */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{t("stats.rate_trend")}</h3>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span className="w-2 h-2 rounded-full bg-[#22c55e]" /> {t("stats.rate_label")}
                </span>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="rateGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={Math.floor(chartData.length / 6)} />
                <YAxis tick={{ fontSize: 11 }} width={30} domain={[0, 100]} unit="%" />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: '0.5rem', fontSize: '0.8rem' }}
                  labelStyle={{ color: 'var(--text-muted)' }}
                  formatter={(value) => [`${value}%`, t("stats.rate_label")]}
                />
                <Area type="monotone" dataKey="rate" stroke="#22c55e" strokeWidth={2} fill="url(#rateGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 源健康度表格 */}
      {sources.length > 0 && (
        <div className="card p-0! overflow-hidden">
          <div className="px-6 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{t("stats.health_title")}</h3>
          </div>
          <table className="table-dark">
            <thead>
              <tr>
                <th>{t("stats.col_name")}</th>
                <th>{t("stats.col_rate")}</th>
                <th>{t("stats.col_total")}</th>
                <th>{t("stats.col_recent")}</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((src) => (
                <tr key={src.source_name}>
                  <td className="font-medium max-w-[220px] truncate" style={{ color: 'var(--text-secondary)' }}>{src.source_name}</td>
                  <td>
                    <span className={`badge ${src.success_rate >= 0.8 ? "badge-success" : src.success_rate >= 0.5 ? "badge-warning" : "badge-danger"}`}>
                      {(src.success_rate * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>{src.total}</td>
                  <td>
                    <div className="flex gap-1">
                      {src.recent.map((status, i) => (
                        <span key={i} className={`dot ${status === 1 ? "dot-success" : status === 0 ? "dot-danger" : "dot-empty"}`} />
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { fetchBriefs, triggerGenerate, fetchGenerateStatus, type BriefRun } from "@/lib/api";

/** 首页：简报列表 + 手动生成 */
export default function HomePage() {
  const { t } = useI18n();
  const [runs, setRuns] = useState<BriefRun[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const size = 10;
  const totalPages = Math.max(1, Math.ceil(total / size));

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchBriefs(page, size);
      setRuns(data.items);
      setTotal(data.total);
    } catch (e) {
      console.error("加载简报列表失败:", e);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await triggerGenerate();
      const poll = setInterval(async () => {
        const status = await fetchGenerateStatus();
        if (status.status !== "running") {
          clearInterval(poll);
          setGenerating(false);
          loadData();
        }
      }, 3000);
    } catch {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 标题行 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{t("home.title")}</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>{t("home.total", { total })}</p>
        </div>
        <button className="btn-primary" disabled={generating} onClick={handleGenerate}>
          {generating ? t("home.generating") : t("home.generate")}
        </button>
      </div>

      {/* KPI 卡片行 */}
      {!loading && runs.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card-sm">
            <div className="kpi-label">{t("home.kpi_total")}</div>
            <div className="kpi-value">{total}</div>
          </div>
          <div className="card-sm">
            <div className="kpi-label">{t("home.kpi_latest")}</div>
            <div className="kpi-value text-xl">{runs[0]?.run_date || "—"}</div>
          </div>
          <div className="card-sm">
            <div className="kpi-label">{t("home.kpi_news")}</div>
            <div className="flex items-baseline gap-2">
              <span className="kpi-value">{runs[0]?.news_count ?? "—"}</span>
              {runs[0] && <span className="kpi-change kpi-change-up">📰</span>}
            </div>
          </div>
          <div className="card-sm">
            <div className="kpi-label">{t("home.kpi_rate")}</div>
            <div className="flex items-baseline gap-2">
              <span className="kpi-value">
                {runs[0] ? `${Math.round((runs[0].success_count / runs[0].total_sources) * 100)}%` : "—"}
              </span>
              {runs[0] && (
                <span
                  className={`kpi-change ${runs[0].success_count / runs[0].total_sources >= 0.8 ? "kpi-change-up" : "kpi-change-down"}`}
                >
                  {runs[0].success_count}/{runs[0].total_sources}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 表格 */}
      {loading ? (
        <div className="card text-center py-16">
          <div className="inline-block w-6 h-6 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
        </div>
      ) : runs.length === 0 ? (
        <div className="card text-center py-16" style={{ color: 'var(--text-muted)' }}>{t("home.empty")}</div>
      ) : (
        <div className="card p-0! overflow-hidden">
          <table className="table-dark">
            <thead>
              <tr>
                <th>{t("home.col_date")}</th>
                <th>{t("home.col_status")}</th>
                <th>{t("home.col_news")}</th>
                <th>{t("home.col_sources")}</th>
                <th>{t("home.col_duration")}</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>
                    <Link
                      href={`/brief/${run.run_date}`}
                      className="font-medium transition-colors hover:text-purple-400"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {run.run_date}
                    </Link>
                  </td>
                  <td>
                    <span
                      className={`badge ${
                        run.status === "success"
                          ? "badge-success"
                          : run.status === "running"
                            ? "badge-warning"
                            : "badge-danger"
                      }`}
                    >
                      <span
                        className={`dot ${run.status === "success" ? "dot-success" : run.status === "running" ? "dot-warning" : "dot-danger"}`}
                      />
                      {run.status === "success"
                        ? t("status.success")
                        : run.status === "running"
                          ? t("status.running")
                          : t("status.failed")}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>{run.news_count}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>
                    {run.success_count}/{run.total_sources}
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{run.duration_sec}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-3">
          <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            {t("home.prev")}
          </button>
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {page} / {totalPages}
          </span>
          <button className="btn-ghost" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
            {t("home.next")}
          </button>
        </div>
      )}
    </div>
  );
}

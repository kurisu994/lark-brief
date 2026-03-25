"use client";

import { useEffect, useState } from "react";
import { Card, Chip, Separator, Spinner } from "@heroui/react";
import { useI18n } from "@/lib/i18n";
import {
  fetchStatsOverview,
  fetchStatsTrend,
  fetchSourcesHealth,
  type StatsOverview,
  type TrendItem,
  type SourceHealth,
} from "@/lib/api";

/** 统计面板页 */
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
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("stats.title")}</h1>

      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label={t("stats.total_runs")} value={overview.total_runs} />
          <KpiCard
            label={t("stats.avg_rate")}
            value={`${(overview.avg_success_rate * 100).toFixed(0)}%`}
            color={overview.avg_success_rate >= 0.8 ? "success" : "warning"}
          />
          <KpiCard label={t("stats.avg_duration")} value={`${overview.avg_duration_sec.toFixed(0)}s`} />
          <KpiCard label={t("stats.avg_news")} value={overview.avg_news_count.toFixed(0)} />
        </div>
      )}

      {trend.length > 0 && (
        <Card>
          <Card.Header>
            <Card.Title>{t("stats.trend_title")}</Card.Title>
          </Card.Header>
          <Separator />
          <Card.Content className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-foreground-secondary border-b border-border">
                  <th className="py-2 pr-4">{t("stats.col_date")}</th>
                  <th className="py-2 pr-4">{t("stats.col_rate")}</th>
                  <th className="py-2 pr-4">{t("stats.col_news")}</th>
                  <th className="py-2 pr-4">{t("stats.col_duration")}</th>
                  <th className="py-2">{t("stats.col_sources")}</th>
                </tr>
              </thead>
              <tbody>
                {trend.map((item) => (
                  <tr key={item.run_date} className="border-b border-border">
                    <td className="py-2 pr-4 font-medium">{item.run_date}</td>
                    <td className="py-2 pr-4">
                      <Chip size="sm" color={item.success_rate >= 0.8 ? "success" : item.success_rate >= 0.5 ? "warning" : "danger"}>
                        {(item.success_rate * 100).toFixed(0)}%
                      </Chip>
                    </td>
                    <td className="py-2 pr-4">{item.news_count}</td>
                    <td className="py-2 pr-4">{item.duration_sec}s</td>
                    <td className="py-2">{item.success_count}/{item.total_sources}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card.Content>
        </Card>
      )}

      {sources.length > 0 && (
        <Card>
          <Card.Header>
            <Card.Title>{t("stats.health_title")}</Card.Title>
          </Card.Header>
          <Separator />
          <Card.Content className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-foreground-secondary border-b border-border">
                  <th className="py-2 pr-4">{t("stats.col_name")}</th>
                  <th className="py-2 pr-4">{t("stats.col_rate")}</th>
                  <th className="py-2 pr-4">{t("stats.col_total")}</th>
                  <th className="py-2">{t("stats.col_recent")}</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((src) => (
                  <tr key={src.source_name} className="border-b border-border">
                    <td className="py-2 pr-4 font-medium max-w-[200px] truncate">{src.source_name}</td>
                    <td className="py-2 pr-4">
                      <Chip size="sm" color={src.success_rate >= 0.8 ? "success" : src.success_rate >= 0.5 ? "warning" : "danger"}>
                        {(src.success_rate * 100).toFixed(0)}%
                      </Chip>
                    </td>
                    <td className="py-2 pr-4">{src.total}</td>
                    <td className="py-2">
                      <div className="flex gap-1">
                        {src.recent.map((status, i) => (
                          <span key={i} className={`w-3 h-3 rounded-full inline-block ${status === 1 ? "bg-success" : status === 0 ? "bg-danger" : "bg-surface-secondary"}`} />
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card.Content>
        </Card>
      )}
    </div>
  );
}

function KpiCard({ label, value, color }: { label: string; value: string | number; color?: "success" | "warning" | "danger" }) {
  return (
    <Card>
      <Card.Content className="text-center py-6">
        <p className="text-foreground-secondary text-sm">{label}</p>
        <p className={`text-3xl font-bold mt-1 ${color === "success" ? "text-success" : color === "warning" ? "text-warning" : color === "danger" ? "text-danger" : "text-foreground"}`}>
          {value}
        </p>
      </Card.Content>
    </Card>
  );
}

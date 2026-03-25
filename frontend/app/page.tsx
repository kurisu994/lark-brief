"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, Button, Chip, Spinner } from "@heroui/react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import {
  fetchBriefs,
  triggerGenerate,
  fetchGenerateStatus,
  type BriefRun,
} from "@/lib/api";

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
    } catch (e) {
      console.error("生成简报失败:", e);
      setGenerating(false);
    }
  };

  const statusText = (status: string) => {
    if (status === "success") return t("status.success");
    if (status === "running") return t("status.running");
    return t("status.failed");
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("home.title")}</h1>
          <p className="text-foreground-secondary text-sm mt-1">
            {t("home.total", { total })}
          </p>
        </div>
        <Button
          variant="primary"
          isDisabled={generating}
          onPress={handleGenerate}
          className="font-semibold"
        >
          {generating ? t("home.generating") : t("home.generate")}
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : runs.length === 0 ? (
        <Card>
          <Card.Content className="text-center py-16 text-foreground-secondary">
            {t("home.empty")}
          </Card.Content>
        </Card>
      ) : (
        <div className="grid gap-3">
          {runs.map((run) => (
            <Link key={run.id} href={`/brief/${run.run_date}`}>
              <Card className="cursor-pointer hover:shadow-md transition-shadow">
                <Card.Content className="flex flex-row items-center justify-between px-6 py-4">
                  <div className="flex items-center gap-4">
                    <div className="text-lg font-semibold">{run.run_date}</div>
                    <Chip
                      size="sm"
                      color={
                        run.status === "success"
                          ? "success"
                          : run.status === "running"
                          ? "warning"
                          : "danger"
                      }
                    >
                      {statusText(run.status)}
                    </Chip>
                  </div>
                  <div className="flex items-center gap-6 text-sm text-foreground-secondary">
                    <span>{t("home.news_count", { count: run.news_count })}</span>
                    <span>{t("home.source_count", { success: run.success_count, total: run.total_sources })}</span>
                    <span>{t("home.duration", { sec: run.duration_sec })}</span>
                  </div>
                </Card.Content>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <Button size="sm" variant="outline" isDisabled={page <= 1} onPress={() => setPage(page - 1)}>
            {t("home.prev")}
          </Button>
          <span className="flex items-center text-sm text-foreground-secondary">
            {page} / {totalPages}
          </span>
          <Button size="sm" variant="outline" isDisabled={page >= totalPages} onPress={() => setPage(page + 1)}>
            {t("home.next")}
          </Button>
        </div>
      )}
    </div>
  );
}

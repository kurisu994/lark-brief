"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Card, Chip, Separator, Spinner } from "@heroui/react";
import ReactMarkdown from "react-markdown";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { fetchBriefDetail, type BriefDetail } from "@/lib/api";

/** 简报详情页 */
export default function BriefPage() {
  const params = useParams();
  const date = params.date as string;
  const { t } = useI18n();
  const [data, setData] = useState<BriefDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchBriefDetail(date)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [date]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <Card.Content className="text-center py-16 text-foreground-secondary">
          {t("detail.not_found", { date })}
          <div className="mt-4">
            <Link href="/" className="text-primary">{t("detail.back")}</Link>
          </div>
        </Card.Content>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-foreground-secondary">
        <Link href="/" className="hover:text-primary">{t("detail.breadcrumb_home")}</Link>
        <span>/</span>
        <span className="text-foreground font-medium">{date}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <Card.Header>
            <Card.Title>{t("detail.brief_title", { date })}</Card.Title>
          </Card.Header>
          <Separator />
          <Card.Content>
            {data.brief_md ? (
              <div className="prose max-w-none">
                <ReactMarkdown>{data.brief_md}</ReactMarkdown>
              </div>
            ) : (
              <p className="text-foreground-secondary">{t("detail.no_content")}</p>
            )}
          </Card.Content>
        </Card>

        <div className="space-y-4">
          {data.run && (
            <Card>
              <Card.Header>
                <Card.Title>{t("detail.run_info")}</Card.Title>
              </Card.Header>
              <Separator />
              <Card.Content className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-foreground-secondary">{t("detail.status")}</span>
                  <Chip size="sm" color={data.run.status === "success" ? "success" : "danger"}>
                    {data.run.status === "success" ? t("status.success") : t("status.failed")}
                  </Chip>
                </div>
                <div className="flex justify-between">
                  <span className="text-foreground-secondary">{t("detail.news_count")}</span>
                  <span className="font-medium">{data.run.news_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-foreground-secondary">{t("detail.success_sources")}</span>
                  <span className="font-medium">{data.run.success_count}/{data.run.total_sources}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-foreground-secondary">{t("detail.duration")}</span>
                  <span className="font-medium">{data.run.duration_sec}s</span>
                </div>
              </Card.Content>
            </Card>
          )}

          {data.sources.length > 0 && (
            <Card>
              <Card.Header>
                <Card.Title>{t("detail.source_detail")}</Card.Title>
              </Card.Header>
              <Separator />
              <Card.Content className="space-y-2 text-sm max-h-96 overflow-y-auto">
                {data.sources
                  .filter((s) => !s.source_name.includes("[LLM]"))
                  .map((src) => (
                    <div key={src.id} className="flex items-center justify-between py-1">
                      <span className="truncate max-w-[180px]">{src.source_name}</span>
                      <Chip size="sm" color={src.success ? "success" : "danger"}>
                        {src.success ? t("status.success") : t("status.failed")}
                      </Chip>
                    </div>
                  ))}
              </Card.Content>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

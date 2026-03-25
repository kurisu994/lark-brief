"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { fetchBriefDetail, type BriefDetail } from "@/lib/api";

/** 简报详情页（自定义解析渲染高颜值卡片） */
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
        <div className="w-6 h-6 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card text-center py-16 animate-fade-in" style={{ color: 'var(--text-muted)' }}>
        <p className="mb-4">{t("detail.not_found", { date })}</p>
        <Link href="/" style={{ color: 'var(--accent)' }}>{t("detail.back")}</Link>
      </div>
    );
  }

  // 解析 Markdown 数据
  const lines = (data.brief_md || "").split('\n');
  const dateLine = lines.find(l => l.includes('年') && l.includes('月') && l.includes('日')) || date;

  const items: { summary: string; url: string }[] = [];
  let currentSummary = "";

  lines.forEach((line) => {
    const numMatch = line.match(/^\d+\.\s+(.*)/);
    if (numMatch) {
      if (currentSummary) {
        items.push({ summary: currentSummary, url: "" });
      }
      currentSummary = numMatch[1];
    } else if (currentSummary && line.trim().startsWith("🔗")) {
      items.push({
        summary: currentSummary,
        url: line.replace(/.*🔗\s*/, "").trim(),
      });
      currentSummary = "";
    }
  });
  if (currentSummary) {
    items.push({ summary: currentSummary, url: "" });
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 面包屑 */}
      <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-muted)' }}>
        <Link href="/" className="transition-colors hover:text-purple-400">{t("detail.breadcrumb_home")}</Link>
        <span>/</span>
        <span style={{ color: 'var(--text-secondary)' }}>{date}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 简报内容 Timeline 视图 */}
        <div className="lg:col-span-2">
          <div className="mb-6 pb-4 border-b" style={{ borderColor: 'var(--border)' }}>
            <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>{t("detail.brief_title", { date })}</h1>
            <p className="text-sm font-medium" style={{ color: 'var(--accent)' }}>{dateLine}</p>
          </div>

          {!items.length ? (
            <p style={{ color: 'var(--text-muted)' }}>{t("detail.no_content")}</p>
          ) : (
            <div className="space-y-5 relative">
              {/* timeline 线条 */}
              <div className="absolute left-[1.125rem] top-8 bottom-8 w-px hidden sm:block" style={{ background: 'var(--border)' }} />
              
              {items.map((item, idx) => (
                <div key={idx} className="relative flex flex-col sm:flex-row items-stretch sm:items-start gap-4 group">
                  {/* 序号气泡 */}
                  <div 
                    className="relative z-10 w-9 h-9 shrink-0 rounded-full border flex items-center justify-center font-bold text-sm transition-all overflow-hidden hidden sm:flex group-hover:!bg-purple-600 group-hover:!text-white group-hover:!border-purple-500 group-hover:shadow-[0_0_20px_rgba(124,58,237,0.3)] shadow-sm"
                    style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', color: 'var(--text-muted)' }}
                  >
                    {idx + 1}
                  </div>
                  
                  {/* 移动端序号 */}
                  <div className="sm:hidden font-bold mb-[-0.5rem] ml-1" style={{ color: 'var(--accent)' }}>#{idx + 1}</div>
                  
                  {/* 内容卡片 */}
                  <div 
                    className="flex-1 card p-5 transition-all group-hover:!border-purple-500/30 group-hover:shadow-[0_4px_24px_rgba(124,58,237,0.08)]"
                    style={{ background: 'var(--bg-card)' }}
                  >
                    <p className="font-[450] text-sm/relaxed sm:text-base/relaxed mb-4" style={{ color: 'var(--text-primary)' }}>
                      {item.summary}
                    </p>
                    {item.url && (
                      <a 
                        href={item.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-xs font-semibold transition-colors px-3 py-1.5 rounded-md hover:opacity-80 border"
                        style={{ color: 'var(--accent)', background: 'var(--purple-bg)', borderColor: 'var(--accent-glow)' }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
                        {t("detail.read_more")}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 侧栏 */}
        <div className="space-y-4">
          {data.run && (
            <div className="card">
              <h3 className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--text-muted)' }}>
                {t("detail.run_info")}
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>{t("detail.status")}</span>
                  <span className={`badge ${data.run.status === "success" ? "badge-success" : "badge-danger"}`}>
                    <span className={`dot ${data.run.status === "success" ? "dot-success" : "dot-danger"}`} />
                    {data.run.status === "success" ? t("status.success") : t("status.failed")}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>{t("detail.news_count")}</span>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{data.run.news_count}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>{t("detail.success_sources")}</span>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{data.run.success_count}/{data.run.total_sources}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>{t("detail.duration")}</span>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{data.run.duration_sec}s</span>
                </div>
              </div>
            </div>
          )}

          {data.sources.length > 0 && (
            <div className="card">
              <h3 className="text-xs font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--text-muted)' }}>
                {t("detail.source_detail")}
              </h3>
              <div className="space-y-2 max-h-[400px] overflow-y-auto custom-scrollbar">
                {data.sources
                  .filter((s) => !s.source_name.includes("[LLM]"))
                  .map((src) => (
                    <div key={src.id} className="flex items-center justify-between py-2 border-b last:border-0 pr-1" style={{ borderColor: 'var(--border)' }}>
                      <span className="text-sm font-medium truncate max-w-[180px]" style={{ color: 'var(--text-secondary)' }}>
                        {src.source_name}
                      </span>
                      <span className={`dot ${src.success ? "dot-success" : "dot-danger"}`} />
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

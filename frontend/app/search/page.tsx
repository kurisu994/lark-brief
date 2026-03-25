"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { searchBriefs, type SearchResult } from "@/lib/api";

/** 搜索页 */
export default function SearchPage() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await searchBriefs(query);
      setResults(data.results);
      setTotal(data.total);
    } catch (e) {
      console.error("搜索失败:", e);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{t("search.title")}</h1>

      {/* 搜索框 */}
      <div className="card">
        <div className="flex gap-3">
          <input
            type="search"
            placeholder={t("search.placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="input-dark flex-1"
          />
          <button className="btn-primary" onClick={handleSearch} disabled={loading}>
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {/* 搜索结果 */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
        </div>
      ) : searched ? (
        results.length > 0 ? (
          <div className="space-y-3">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {t("search.result_count", { total, query })}
            </p>
            {results.map((r) => (
              <Link key={r.date} href={`/brief/${r.date}`}>
                <div className="card hover:border-purple-500/20 transition-all cursor-pointer group mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold group-hover:text-purple-400 transition-colors" style={{ color: 'var(--text-primary)' }}>{r.date}</span>
                    <span className="badge badge-purple">
                      {t("search.match_count", { count: r.match_count })}
                    </span>
                  </div>
                  <p className="text-sm line-clamp-2" style={{ color: 'var(--text-muted)' }}>{r.snippet}</p>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="card text-center py-12" style={{ color: 'var(--text-muted)' }}>
            {t("search.no_result", { query })}
          </div>
        )
      ) : null}
    </div>
  );
}

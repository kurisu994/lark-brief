"use client";

import { useState, useCallback } from "react";
import { Card, Input, Chip, Spinner } from "@heroui/react";
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
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("search.title")}</h1>

      <Card>
        <Card.Content className="p-4">
          <Input
            type="search"
            placeholder={t("search.placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full"
          />
        </Card.Content>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : searched ? (
        results.length > 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-foreground-secondary">
              {t("search.result_count", { total, query })}
            </p>
            {results.map((r) => (
              <Link key={r.date} href={`/brief/${r.date}`}>
                <Card className="cursor-pointer hover:shadow-md transition-shadow">
                  <Card.Content className="px-6 py-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{r.date}</span>
                      <Chip size="sm" color="accent">
                        {t("search.match_count", { count: r.match_count })}
                      </Chip>
                    </div>
                    <p className="text-sm text-foreground-secondary line-clamp-2">
                      {r.snippet}
                    </p>
                  </Card.Content>
                </Card>
              </Link>
            ))}
          </div>
        ) : (
          <Card>
            <Card.Content className="text-center py-12 text-foreground-secondary">
              {t("search.no_result", { query })}
            </Card.Content>
          </Card>
        )
      ) : null}
    </div>
  );
}

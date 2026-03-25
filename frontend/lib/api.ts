/** API 服务层：封装对后端 FastAPI 接口的请求 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

/** 通用请求封装 */
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API 请求失败: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ========== 类型定义 ==========

export interface BriefRun {
  id: number;
  run_date: string;
  started_at: string;
  finished_at: string | null;
  total_sources: number;
  success_count: number;
  fail_count: number;
  news_count: number;
  duration_sec: number;
  status: string;
  total_configured: number;
  success_rate: number;
  has_brief: boolean;
}

export interface BriefListResponse {
  items: BriefRun[];
  total: number;
  page: number;
  size: number;
}

export interface SourceLog {
  id: number;
  run_id: number;
  source_name: string;
  url: string;
  success: number;
  error_msg: string;
  char_count: number;
  news_count: number;
}

export interface BriefDetail {
  run: BriefRun | null;
  sources: SourceLog[];
  brief_md: string;
}

export interface StatsOverview {
  total_runs: number;
  avg_success_rate: number;
  avg_duration_sec: number;
  avg_news_count: number;
  total_configured: number;
}

export interface TrendItem {
  run_date: string;
  total_sources: number;
  success_count: number;
  success_rate: number;
  news_count: number;
  duration_sec: number;
}

export interface SourceHealth {
  source_name: string;
  total: number;
  success_count: number;
  success_rate: number;
  recent: (number | null)[];
}

export interface SearchResult {
  date: string;
  match_count: number;
  snippet: string;
}

export interface GenerateStatus {
  status: "idle" | "running" | "completed" | "failed" | "cancelled";
  message: string;
}

// ========== API 方法 ==========

/** 获取简报列表 */
export function fetchBriefs(page = 1, size = 20) {
  return request<BriefListResponse>(`/api/briefs?page=${page}&size=${size}`);
}

/** 获取简报详情 */
export function fetchBriefDetail(date: string) {
  return request<BriefDetail>(`/api/briefs/${date}`);
}

/** 获取统计概览 */
export function fetchStatsOverview() {
  return request<StatsOverview>("/api/stats/overview");
}

/** 获取成功率趋势 */
export function fetchStatsTrend(days = 30) {
  return request<{ days: number; data: TrendItem[] }>(`/api/stats/trend?days=${days}`);
}

/** 获取源健康度 */
export function fetchSourcesHealth(days = 7) {
  return request<{ days: number; data: SourceHealth[] }>(`/api/stats/sources?days=${days}`);
}

/** 全文搜索 */
export function searchBriefs(query: string) {
  return request<{ query: string; total: number; results: SearchResult[] }>(
    `/api/search?q=${encodeURIComponent(query)}`
  );
}

/** 触发生成简报 */
export function triggerGenerate() {
  return request<GenerateStatus>("/api/generate", { method: "POST" });
}

/** 查询生成状态 */
export function fetchGenerateStatus() {
  return request<GenerateStatus>("/api/generate/status");
}

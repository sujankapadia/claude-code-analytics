/** Typed API client for the FastAPI backend. */

import type {
  ActiveSessionsResponse,
  AggregateActivity,
  ActivityMetrics,
  AnalysisResult,
  AnalysisTypeInfo,
  Bookmark,
  DailyStats,
  FindPromptsResponse,
  FindSessionsResponse,
  HeatmapCell,
  McpStats,
  Message,
  ProjectActivity,
  ProjectSummary,
  ProviderInfo,
  ProviderModel,
  Project,
  PublishResult,
  SearchResponse,
  SessionSummary,
  Session,
  TextVolume,
  TokenTimelinePoint,
  TokenUsage,
  ToolUsageSummary,
  ToolUse,
} from "./types";

const BASE = "/api";

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// -- Projects --

export const fetchProjects = () => get<ProjectSummary[]>("/projects");

export const fetchProject = (id: string) => get<Project>(`/projects/${id}`);

// -- Sessions --

export const fetchSessions = (params?: { project_id?: string; limit?: number }) =>
  get<SessionSummary[]>("/sessions", params);

export const fetchSession = (id: string) => get<Session>(`/sessions/${id}`);

export const fetchSessionMessages = (id: string) => get<Message[]>(`/sessions/${id}/messages`);

export const fetchSessionToolUses = (id: string) => get<ToolUse[]>(`/sessions/${id}/tool-uses`);

export const fetchSessionTokens = (id: string) => get<TokenUsage>(`/sessions/${id}/tokens`);

export const fetchSessionTokenTimeline = (id: string) =>
  get<TokenTimelinePoint[]>(`/sessions/${id}/tokens/timeline`);

export const fetchSessionActivity = (id: string, idleCap?: number) =>
  get<ActivityMetrics>(`/sessions/${id}/activity`, { idle_cap: idleCap });

export const fetchSessionTextVolume = (id: string) =>
  get<TextVolume>(`/sessions/${id}/text-volume`);

// -- Search --

export const fetchSearch = (params: {
  q: string;
  scope?: string;
  project_id?: string;
  tool_name?: string;
  start_date?: string;
  end_date?: string;
  per_page?: number;
  page?: number;
}) => get<SearchResponse>("/search", params);

// -- Analytics --

export const fetchDailyStats = (days?: number) =>
  get<DailyStats[]>("/analytics/daily", { days });

export const fetchToolStats = () => get<ToolUsageSummary[]>("/analytics/tools");

export const fetchToolNames = () => get<string[]>("/analytics/tools/names");

export const fetchMcpStats = () => get<McpStats>("/analytics/tools/mcp");

export const fetchHeatmap = (days?: number) =>
  get<HeatmapCell[]>("/analytics/heatmap", { days });

export const fetchActivityMetrics = (params?: { project_id?: string; idle_cap?: number }) =>
  get<AggregateActivity>("/analytics/activity", params);

export const fetchActivityByProject = () =>
  get<ProjectActivity[]>("/analytics/activity/by-project");

// -- Active Sessions --

export const fetchActiveSessions = (params?: { include_recent?: boolean; recent_minutes?: number }) =>
  get<ActiveSessionsResponse>("/active-sessions", params as Record<string, string | number | undefined>);

// -- Bookmarks --

export const fetchBookmarks = (params?: { project_id?: string }) =>
  get<Bookmark[]>("/bookmarks", params);

export const fetchSessionBookmarks = (sessionId: string) =>
  get<Bookmark[]>(`/bookmarks/by-session/${sessionId}`);

export async function createBookmark(params: {
  session_id: string;
  message_index: number;
  name: string;
  description?: string;
}): Promise<Bookmark> {
  const res = await fetch(`${BASE}/bookmarks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<Bookmark>;
}

export async function updateBookmark(
  id: number,
  params: { name?: string; description?: string },
): Promise<Bookmark> {
  const res = await fetch(`${BASE}/bookmarks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<Bookmark>;
}

export async function deleteBookmark(id: number): Promise<void> {
  const res = await fetch(`${BASE}/bookmarks/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
}

// -- Analysis --

export const fetchAnalysisTypes = () =>
  get<Record<string, AnalysisTypeInfo>>("/analysis/types");

export const fetchProviderInfo = () =>
  get<ProviderInfo>("/analysis/provider-info");

export async function fetchProviderModels(params: {
  base_url: string;
  api_key?: string;
}): Promise<ProviderModel[]> {
  const res = await fetch(`${BASE}/analysis/models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<ProviderModel[]>;
}

export async function runAnalysis(params: {
  session_id: string;
  analysis_type: string;
  custom_prompt?: string;
  model?: string;
  start_time?: string;
  end_time?: string;
  message_index?: number;
  context_window?: number;
  base_url?: string;
  api_key?: string;
}): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/analysis/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<AnalysisResult>;
}

// -- Examples --

export async function findExamplePrompts(params: {
  query: string;
  project_id?: string;
  max_results?: number;
}): Promise<FindPromptsResponse> {
  const res = await fetch(`${BASE}/examples/prompts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<FindPromptsResponse>;
}

export async function findExampleSessions(params: {
  query: string;
  project_id?: string;
  max_results?: number;
  scope?: string;
  role?: string;
}): Promise<FindSessionsResponse> {
  const res = await fetch(`${BASE}/examples/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<FindSessionsResponse>;
}

export async function publishAnalysis(params: {
  analysis_content: string;
  session_content?: string;
  description?: string;
  is_public?: boolean;
}): Promise<PublishResult> {
  const res = await fetch(`${BASE}/analysis/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<PublishResult>;
}

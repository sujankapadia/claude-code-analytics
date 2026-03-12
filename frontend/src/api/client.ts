/** Typed API client for the FastAPI backend. */

import type {
  AggregateActivity,
  ActivityMetrics,
  DailyStats,
  HeatmapCell,
  McpStats,
  Message,
  ProjectSummary,
  Project,
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

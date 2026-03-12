/** API response types matching the Pydantic models on the backend. */

export interface ProjectSummary {
  project_id: string;
  project_name: string;
  total_sessions: number;
  first_session: string | null;
  last_session: string | null;
  total_messages: number;
  total_tool_uses: number;
  total_input_tokens: number;
  total_output_tokens: number;
}

export interface Project {
  project_id: string;
  project_name: string;
  created_at: string;
}

export interface SessionSummary {
  session_id: string;
  project_id: string;
  project_name: string;
  start_time: string | null;
  end_time: string | null;
  duration_seconds: number | null;
  message_count: number;
  tool_use_count: number;
  user_message_count: number;
  assistant_message_count: number;
}

export interface Session {
  session_id: string;
  project_id: string;
  start_time: string | null;
  end_time: string | null;
  message_count: number;
  tool_use_count: number;
  created_at: string;
}

export interface Message {
  message_id: number;
  session_id: string;
  message_index: number;
  role: string;
  content: string | null;
  timestamp: string;
  input_tokens: number | null;
  output_tokens: number | null;
  cache_creation_input_tokens: number | null;
  cache_read_input_tokens: number | null;
  cache_ephemeral_5m_tokens: number | null;
  cache_ephemeral_1h_tokens: number | null;
}

export interface ToolUse {
  tool_use_id: string;
  session_id: string;
  message_index: number;
  tool_name: string;
  tool_input: string | null;
  tool_result: string | null;
  is_error: boolean;
  timestamp: string;
}

export interface ToolUsageSummary {
  tool_name: string;
  total_uses: number;
  error_count: number;
  error_rate_percent: number;
  sessions_used_in: number;
  first_used: string | null;
  last_used: string | null;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  cache_creation_tokens: number;
  cache_read_tokens: number;
  cache_5m_tokens: number;
  cache_1h_tokens: number;
}

export interface TokenTimelinePoint {
  timestamp: string;
  cumulative_tokens: number;
  input_tokens: number;
  output_tokens: number;
}

export interface ActivityMetrics {
  active_time_seconds: number;
  total_duration_seconds: number;
  idle_ratio: number;
}

export interface TextVolume {
  user_text_chars: number;
  assistant_text_chars: number;
  tool_output_chars: number;
}

export interface DailyStats {
  date: string;
  sessions: number;
  messages: number;
  user_messages: number;
  assistant_messages: number;
  input_tokens: number;
  output_tokens: number;
}

export interface McpStats {
  total_uses: number;
  total_sessions: number;
  by_tool: Array<{ tool_name: string; use_count: number; session_count: number }>;
  by_server: Array<{ mcp_server: string; total_uses: number; session_count: number }>;
}

export interface AggregateActivity {
  total_active_time_seconds: number;
  total_wall_time_seconds: number;
  overall_idle_ratio: number;
  total_user_text_chars: number;
  total_assistant_text_chars: number;
  total_tool_output_chars: number;
  session_count: number;
  avg_active_time_per_session: number;
}

export interface SearchResult {
  session_id: string;
  message_index: number;
  result_type: string;
  detail: string;
  matched_content: string;
  snippet: string | null;
  timestamp: string;
  project_id: string;
  project_name: string;
}

export interface SearchResponse {
  results_by_session: Record<string, SearchResult[]>;
  has_more: boolean;
  total_sessions: number;
}

export interface HeatmapCell {
  day_of_week: number;
  hour: number;
  message_count: number;
  session_count: number;
}

export interface SSEvent {
  type: string;
  [key: string]: unknown;
}

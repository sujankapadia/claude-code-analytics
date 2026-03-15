import { useQuery } from "@tanstack/react-query";
import {
  fetchToolStats,
  fetchDailyStats,
  fetchMcpStats,
  fetchHeatmap,
  fetchActivityMetrics,
  fetchProjects,
  fetchActivityByProject,
} from "@/api/client";
import { ActivityHeatmap } from "@/components/activity-heatmap";
import { TokenAreaChart } from "@/components/charts/token-area-chart";
import { MessagesAreaChart } from "@/components/charts/messages-area-chart";
import { MessagesByProjectDonut } from "@/components/charts/messages-by-project-donut";
import { ActiveTimeBarChart } from "@/components/charts/active-time-bar-chart";
import { formatNumber, formatDuration, shortProjectName } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function AnalyticsPage() {
  const { data: tools } = useQuery({
    queryKey: ["analytics", "tools"],
    queryFn: fetchToolStats,
  });

  const { data: daily } = useQuery({
    queryKey: ["analytics", "daily", 30],
    queryFn: () => fetchDailyStats(30),
  });

  const { data: mcp } = useQuery({
    queryKey: ["analytics", "mcp"],
    queryFn: fetchMcpStats,
  });

  const { data: heatmap } = useQuery({
    queryKey: ["analytics", "heatmap"],
    queryFn: () => fetchHeatmap(90),
  });

  const { data: activity } = useQuery({
    queryKey: ["analytics", "activity"],
    queryFn: () => fetchActivityMetrics(),
  });

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  const { data: projectActivity } = useQuery({
    queryKey: ["analytics", "activity-by-project"],
    queryFn: fetchActivityByProject,
  });

  const maxToolUses = tools
    ? Math.max(...tools.map((t) => t.total_uses))
    : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {/* Top row: charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {daily && daily.length > 0 && <MessagesAreaChart data={daily} />}
        {daily && daily.length > 0 && <TokenAreaChart data={daily} />}
      </div>

      {/* Second row: heatmap + donut */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-medium text-muted-foreground">
            Activity Heatmap (last 90 days)
          </h2>
          {heatmap ? (
            <ActivityHeatmap data={heatmap} />
          ) : (
            <div className="h-32 animate-pulse rounded bg-muted" />
          )}
        </div>
        {projects && projects.length > 0 && (
          <MessagesByProjectDonut data={projects} />
        )}
      </div>

      {/* Activity stats */}
      {activity && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatMini
            label="Total Active Time"
            value={formatDuration(activity.total_active_time_seconds)}
          />
          <StatMini
            label="Avg per Session"
            value={formatDuration(activity.avg_active_time_per_session)}
          />
          <StatMini
            label="Sessions Analyzed"
            value={activity.session_count.toString()}
          />
        </div>
      )}

      {/* Active time bar chart */}
      {projectActivity && projectActivity.length > 0 && (
        <ActiveTimeBarChart data={projectActivity} />
      )}

      {/* Per-project activity table */}
      {projectActivity && projectActivity.length > 0 && (
        <div className="rounded-lg border">
          <div className="border-b px-4 py-3">
            <h2 className="text-sm font-medium">Project Activity Breakdown</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="px-4 py-2 font-medium">Project</th>
                  <th className="px-4 py-2 font-medium text-right">Sessions</th>
                  <th className="px-4 py-2 font-medium text-right">Active</th>
                  <th className="px-4 py-2 font-medium text-right">User Chars</th>
                  <th className="px-4 py-2 font-medium text-right">Asst Chars</th>
                  <th className="px-4 py-2 font-medium text-right">Tool Output</th>
                  <th className="px-4 py-2 font-medium text-right">Text Split</th>
                </tr>
              </thead>
              <tbody>
                {projectActivity
                  .slice()
                  .sort((a, b) => b.active_time_seconds - a.active_time_seconds)
                  .map((p) => {
                    const totalChars =
                      p.user_text_chars +
                      p.assistant_text_chars +
                      p.tool_output_chars;
                    const userPct =
                      totalChars > 0
                        ? ((p.user_text_chars / totalChars) * 100).toFixed(0)
                        : "0";
                    const asstPct =
                      totalChars > 0
                        ? ((p.assistant_text_chars / totalChars) * 100).toFixed(0)
                        : "0";
                    const toolPct =
                      totalChars > 0
                        ? ((p.tool_output_chars / totalChars) * 100).toFixed(0)
                        : "0";
                    return (
                      <tr
                        key={p.project_id}
                        className="border-b last:border-0 hover:bg-muted/50"
                      >
                        <td className="max-w-[200px] truncate px-4 py-2 font-mono text-xs" title={p.project_name}>
                          {shortProjectName(p.project_name)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {p.session_count}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {formatDuration(p.active_time_seconds)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {formatNumber(p.user_text_chars)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {formatNumber(p.assistant_text_chars)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {formatNumber(p.tool_output_chars)}
                        </td>
                        <td className="px-4 py-2 text-right text-xs text-muted-foreground tabular-nums">
                          {userPct}% user · {asstPct}% asst · {toolPct}% tool
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tool usage with bars */}
      <div className="rounded-lg border">
        <div className="border-b px-4 py-3">
          <h2 className="text-sm font-medium">Tool Usage</h2>
        </div>
        <div className="divide-y">
          {tools?.map((t) => {
            const pct =
              maxToolUses > 0 ? (t.total_uses / maxToolUses) * 100 : 0;
            return (
              <div
                key={t.tool_name}
                className="relative px-4 py-2 hover:bg-muted/30"
              >
                {/* Background bar */}
                <div
                  className="absolute inset-y-0 left-0 bg-primary/5"
                  style={{ width: `${pct}%` }}
                />
                <div className="relative flex items-center gap-4">
                  <span className="w-48 shrink-0 truncate font-mono text-sm font-medium">
                    {t.tool_name}
                  </span>
                  <span className="w-16 text-right text-sm tabular-nums">
                    {formatNumber(t.total_uses)}
                  </span>
                  <span
                    className={cn(
                      "w-20 text-right text-xs tabular-nums",
                      t.error_rate_percent > 10
                        ? "text-red-500"
                        : t.error_rate_percent > 0
                          ? "text-amber-500"
                          : "text-muted-foreground"
                    )}
                  >
                    {t.error_count > 0
                      ? `${t.error_count} err (${t.error_rate_percent.toFixed(1)}%)`
                      : "—"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {t.sessions_used_in} sessions
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* MCP stats */}
      {mcp && mcp.total_uses > 0 && (
        <div className="rounded-lg border">
          <div className="border-b px-4 py-3">
            <h2 className="text-sm font-medium">
              MCP Tools ({formatNumber(mcp.total_uses)} total uses)
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="px-4 py-2 font-medium">Server</th>
                  <th className="px-4 py-2 font-medium text-right">Uses</th>
                  <th className="px-4 py-2 font-medium text-right">
                    Sessions
                  </th>
                </tr>
              </thead>
              <tbody>
                {mcp.by_server.map((s) => (
                  <tr
                    key={s.mcp_server}
                    className="border-b last:border-0 hover:bg-muted/50"
                  >
                    <td className="px-4 py-2 font-mono">{s.mcp_server}</td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {s.total_uses}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {s.session_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StatMini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold">{value}</p>
    </div>
  );
}

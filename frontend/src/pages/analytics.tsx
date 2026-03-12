import { useQuery } from "@tanstack/react-query";
import {
  fetchToolStats,
  fetchDailyStats,
  fetchMcpStats,
  fetchHeatmap,
  fetchActivityMetrics,
} from "@/api/client";
import { ActivityHeatmap } from "@/components/activity-heatmap";
import { cn } from "@/lib/utils";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

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

  const maxToolUses = tools
    ? Math.max(...tools.map((t) => t.total_uses))
    : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {/* Top row: daily chart + heatmap */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Daily stats bar chart */}
        {daily && daily.length > 0 && (
          <div className="rounded-lg border bg-card p-4">
            <h2 className="mb-3 text-sm font-medium text-muted-foreground">
              Daily Messages (last 30 days)
            </h2>
            <div
              className="flex items-end gap-0.5"
              style={{ height: 120 }}
            >
              {daily
                .slice()
                .reverse()
                .map((d) => {
                  const max = Math.max(...daily.map((dd) => dd.messages));
                  const pct = max > 0 ? (d.messages / max) * 100 : 0;
                  const tokenPct =
                    max > 0
                      ? ((d.input_tokens + d.output_tokens) /
                          Math.max(
                            ...daily.map(
                              (dd) => dd.input_tokens + dd.output_tokens
                            )
                          )) *
                        100
                      : 0;
                  return (
                    <div
                      key={d.date}
                      className="group relative flex-1"
                      style={{ height: "100%" }}
                    >
                      {/* Token bar (behind) */}
                      <div
                        className="absolute bottom-0 w-full rounded-sm bg-chart-2/30"
                        style={{ height: `${Math.max(tokenPct, 1)}%` }}
                      />
                      {/* Message bar (front) */}
                      <div
                        className="absolute bottom-0 w-full rounded-sm bg-chart-1/70 transition-colors group-hover:bg-chart-1"
                        style={{ height: `${Math.max(pct, 2)}%` }}
                      />
                      <div className="pointer-events-none absolute -top-8 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-popover px-1.5 py-0.5 text-[10px] text-popover-foreground shadow group-hover:block">
                        {d.date}
                        <br />
                        {d.messages} msgs ·{" "}
                        {formatNumber(d.input_tokens + d.output_tokens)} tokens
                      </div>
                    </div>
                  );
                })}
            </div>
            <div className="mt-2 flex items-center gap-3 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="inline-block size-2 rounded-sm bg-chart-1/70" />
                Messages
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block size-2 rounded-sm bg-chart-2/30" />
                Tokens
              </span>
            </div>
          </div>
        )}

        {/* Activity heatmap */}
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
            label="Idle Ratio"
            value={`${(activity.overall_idle_ratio * 100).toFixed(0)}%`}
          />
          <StatMini
            label="Sessions Analyzed"
            value={activity.session_count.toString()}
          />
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

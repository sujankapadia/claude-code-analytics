import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  fetchProjects,
  fetchDailyStats,
  fetchActivityMetrics,
  fetchHeatmap,
} from "@/api/client";
import { ActivityHeatmap } from "@/components/activity-heatmap";

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

export default function DashboardPage() {
  const { data: projects, isPending: projectsLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  const { data: dailyStats } = useQuery({
    queryKey: ["analytics", "daily"],
    queryFn: () => fetchDailyStats(30),
  });

  const { data: activity } = useQuery({
    queryKey: ["analytics", "activity"],
    queryFn: () => fetchActivityMetrics(),
  });

  const { data: heatmap } = useQuery({
    queryKey: ["analytics", "heatmap"],
    queryFn: () => fetchHeatmap(90),
  });

  const totalSessions =
    projects?.reduce((s, p) => s + p.total_sessions, 0) ?? 0;
  const totalMessages =
    projects?.reduce((s, p) => s + p.total_messages, 0) ?? 0;
  const totalTokens =
    projects?.reduce(
      (s, p) => s + p.total_input_tokens + p.total_output_tokens,
      0
    ) ?? 0;

  // Sort projects by total tokens desc for the table
  const sortedProjects = projects
    ?.slice()
    .sort(
      (a, b) =>
        b.total_input_tokens +
        b.total_output_tokens -
        (a.total_input_tokens + a.total_output_tokens)
    );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <KpiCard
          label="Projects"
          value={projects?.length ?? 0}
          loading={projectsLoading}
        />
        <KpiCard
          label="Sessions"
          value={totalSessions}
          loading={projectsLoading}
        />
        <KpiCard
          label="Messages"
          value={formatNumber(totalMessages)}
          loading={projectsLoading}
        />
        <KpiCard
          label="Tokens"
          value={formatNumber(totalTokens)}
          loading={projectsLoading}
        />
        <KpiCard
          label="Active Time"
          value={
            activity ? formatDuration(activity.total_active_time_seconds) : "—"
          }
          loading={!activity}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Activity heatmap */}
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-medium text-muted-foreground">
            Activity (last 90 days)
          </h2>
          {heatmap ? (
            <ActivityHeatmap data={heatmap} />
          ) : (
            <div className="h-32 animate-pulse rounded bg-muted" />
          )}
        </div>

        {/* Recent activity sparkline */}
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-medium text-muted-foreground">
            Messages (last 30 days)
          </h2>
          {dailyStats && dailyStats.length > 0 ? (
            <div className="flex items-end gap-0.5" style={{ height: 100 }}>
              {dailyStats
                .slice()
                .reverse()
                .map((d) => {
                  const max = Math.max(...dailyStats.map((dd) => dd.messages));
                  const pct = max > 0 ? (d.messages / max) * 100 : 0;
                  return (
                    <div
                      key={d.date}
                      className="group relative flex-1"
                      style={{ height: "100%" }}
                    >
                      <div
                        className="absolute bottom-0 w-full rounded-sm bg-primary/60 transition-colors group-hover:bg-primary"
                        style={{ height: `${Math.max(pct, 2)}%` }}
                      />
                      <div className="pointer-events-none absolute -top-6 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-popover px-1.5 py-0.5 text-[10px] text-popover-foreground shadow group-hover:block">
                        {d.date}: {d.messages} msgs
                      </div>
                    </div>
                  );
                })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No data</p>
          )}
        </div>
      </div>

      {/* Tool usage overview */}
      {activity && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatMini
            label="User Text"
            value={formatNumber(activity.total_user_text_chars) + " chars"}
          />
          <StatMini
            label="Assistant Text"
            value={
              formatNumber(activity.total_assistant_text_chars) + " chars"
            }
          />
          <StatMini
            label="Tool Output"
            value={formatNumber(activity.total_tool_output_chars) + " chars"}
          />
          <StatMini
            label="Avg Session"
            value={formatDuration(activity.avg_active_time_per_session)}
          />
        </div>
      )}

      {/* Projects table */}
      <div className="rounded-lg border">
        <div className="border-b px-4 py-3">
          <h2 className="text-sm font-medium">Projects</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="px-4 py-2 font-medium">Project</th>
                <th className="px-4 py-2 font-medium text-right">Sessions</th>
                <th className="px-4 py-2 font-medium text-right">Messages</th>
                <th className="px-4 py-2 font-medium text-right">
                  Tool Uses
                </th>
                <th className="px-4 py-2 font-medium text-right">Tokens</th>
              </tr>
            </thead>
            <tbody>
              {sortedProjects?.map((p) => {
                const shortName =
                  p.project_name.split("/").pop() ?? p.project_name;
                const tokens =
                  p.total_input_tokens + p.total_output_tokens;
                return (
                  <tr
                    key={p.project_id}
                    className="border-b last:border-0 hover:bg-muted/50"
                  >
                    <td className="px-4 py-2">
                      <Link
                        to={`/sessions?project_id=${p.project_id}`}
                        className="font-medium hover:underline"
                        title={p.project_name}
                      >
                        {shortName}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {p.total_sessions}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {formatNumber(p.total_messages)}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {formatNumber(p.total_tool_uses)}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {formatNumber(tokens)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  loading,
}: {
  label: string;
  value: string | number;
  loading: boolean;
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      {loading ? (
        <div className="mt-1 h-8 w-16 animate-pulse rounded bg-muted" />
      ) : (
        <p className="mt-1 text-2xl font-bold">{value}</p>
      )}
    </div>
  );
}

function StatMini({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold">{value}</p>
    </div>
  );
}

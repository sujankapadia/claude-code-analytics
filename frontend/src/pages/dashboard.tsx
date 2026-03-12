import { useQuery } from "@tanstack/react-query";
import { fetchProjects, fetchDailyStats, fetchActivityMetrics } from "@/api/client";

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

  const totalSessions = projects?.reduce((s, p) => s + p.total_sessions, 0) ?? 0;
  const totalMessages = projects?.reduce((s, p) => s + p.total_messages, 0) ?? 0;
  const totalTokens = projects?.reduce(
    (s, p) => s + p.total_input_tokens + p.total_output_tokens,
    0
  ) ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Projects" value={projects?.length ?? 0} loading={projectsLoading} />
        <KpiCard label="Sessions" value={totalSessions} loading={projectsLoading} />
        <KpiCard label="Messages" value={formatNumber(totalMessages)} loading={projectsLoading} />
        <KpiCard
          label="Active Time"
          value={activity ? formatDuration(activity.total_active_time_seconds) : "—"}
          loading={!activity}
        />
      </div>

      {/* Token summary */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-medium text-muted-foreground">Token Usage</h2>
          <p className="text-3xl font-bold">{formatNumber(totalTokens)}</p>
          <p className="text-sm text-muted-foreground">total tokens across all sessions</p>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-medium text-muted-foreground">
            Recent Activity (30 days)
          </h2>
          {dailyStats && dailyStats.length > 0 ? (
            <div className="flex items-end gap-0.5" style={{ height: 64 }}>
              {dailyStats
                .slice()
                .reverse()
                .map((d) => {
                  const max = Math.max(...dailyStats.map((dd) => dd.messages));
                  const pct = max > 0 ? (d.messages / max) * 100 : 0;
                  return (
                    <div
                      key={d.date}
                      className="flex-1 rounded-sm bg-primary/60"
                      style={{ height: `${Math.max(pct, 2)}%` }}
                      title={`${d.date}: ${d.messages} messages`}
                    />
                  );
                })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No data</p>
          )}
        </div>
      </div>

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
                <th className="px-4 py-2 font-medium text-right">Tool Uses</th>
                <th className="px-4 py-2 font-medium text-right">Tokens</th>
              </tr>
            </thead>
            <tbody>
              {projects?.map((p) => (
                <tr key={p.project_id} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-2 font-medium">{p.project_name}</td>
                  <td className="px-4 py-2 text-right">{p.total_sessions}</td>
                  <td className="px-4 py-2 text-right">{formatNumber(p.total_messages)}</td>
                  <td className="px-4 py-2 text-right">{formatNumber(p.total_tool_uses)}</td>
                  <td className="px-4 py-2 text-right">
                    {formatNumber(p.total_input_tokens + p.total_output_tokens)}
                  </td>
                </tr>
              ))}
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

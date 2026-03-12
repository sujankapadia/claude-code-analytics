import { useQuery } from "@tanstack/react-query";
import { fetchToolStats, fetchDailyStats, fetchMcpStats } from "@/api/client";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
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

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {/* Daily stats */}
      {daily && daily.length > 0 && (
        <div className="rounded-lg border bg-card p-4">
          <h2 className="mb-3 text-sm font-medium text-muted-foreground">
            Daily Messages (last 30 days)
          </h2>
          <div className="flex items-end gap-0.5" style={{ height: 80 }}>
            {daily
              .slice()
              .reverse()
              .map((d) => {
                const max = Math.max(...daily.map((dd) => dd.messages));
                const pct = max > 0 ? (d.messages / max) * 100 : 0;
                return (
                  <div
                    key={d.date}
                    className="flex-1 rounded-sm bg-chart-1/70"
                    style={{ height: `${Math.max(pct, 2)}%` }}
                    title={`${d.date}: ${d.messages} msgs, ${formatNumber(d.input_tokens + d.output_tokens)} tokens`}
                  />
                );
              })}
          </div>
        </div>
      )}

      {/* Tool usage table */}
      <div className="rounded-lg border">
        <div className="border-b px-4 py-3">
          <h2 className="text-sm font-medium">Tool Usage</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="px-4 py-2 font-medium">Tool</th>
                <th className="px-4 py-2 font-medium text-right">Uses</th>
                <th className="px-4 py-2 font-medium text-right">Errors</th>
                <th className="px-4 py-2 font-medium text-right">Error Rate</th>
                <th className="px-4 py-2 font-medium text-right">Sessions</th>
              </tr>
            </thead>
            <tbody>
              {tools?.map((t) => (
                <tr key={t.tool_name} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-2 font-mono font-medium">{t.tool_name}</td>
                  <td className="px-4 py-2 text-right">{formatNumber(t.total_uses)}</td>
                  <td className="px-4 py-2 text-right">{t.error_count}</td>
                  <td className="px-4 py-2 text-right">{t.error_rate_percent}%</td>
                  <td className="px-4 py-2 text-right">{t.sessions_used_in}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
                  <th className="px-4 py-2 font-medium text-right">Sessions</th>
                </tr>
              </thead>
              <tbody>
                {mcp.by_server.map((s) => (
                  <tr key={s.mcp_server} className="border-b last:border-0 hover:bg-muted/50">
                    <td className="px-4 py-2 font-mono">{s.mcp_server}</td>
                    <td className="px-4 py-2 text-right">{s.total_uses}</td>
                    <td className="px-4 py-2 text-right">{s.session_count}</td>
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

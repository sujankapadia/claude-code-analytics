import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import type { ProjectSummary } from "@/api/types";
import { formatNumber, getChartColors, shortProjectName } from "@/lib/format";

export function MessagesByProjectDonut({
  data,
}: {
  data: ProjectSummary[];
}) {
  const palette = getChartColors();
  // Extend palette for 10 items by adjusting opacity
  const COLORS = [
    ...palette,
    ...palette.map((c) => c.replace(")", " / 0.6)")),
  ];

  const top10 = data.slice(0, 10).map((p) => ({
    name: p.project_name,
    value: p.total_messages,
  }));

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="mb-3 text-sm font-medium text-muted-foreground">
        Messages by Project (top 10)
      </h2>
      <div className="flex items-center gap-4">
        <ResponsiveContainer width="50%" height={220}>
          <PieChart>
            <Pie
              data={top10}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              dataKey="value"
              paddingAngle={2}
            >
              {top10.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => formatNumber(Number(value))} />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex flex-col gap-1 text-xs">
          {top10.map((entry, i) => (
            <div key={entry.name} className="flex items-center gap-1.5">
              <span
                className="inline-block size-2 shrink-0 rounded-sm"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <span className="truncate" title={entry.name}>
                {shortProjectName(entry.name)}
              </span>
              <span className="ml-auto tabular-nums text-muted-foreground">
                {formatNumber(entry.value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { ProjectActivity } from "@/api/types";
import { formatDuration, getChartColors, shortProjectName } from "@/lib/format";

export function ActiveTimeBarChart({ data }: { data: ProjectActivity[] }) {
  const [c1, c2] = getChartColors();

  const sorted = data
    .slice()
    .sort((a, b) => b.active_time_seconds - a.active_time_seconds)
    .slice(0, 15);

  const chartData = sorted.map((p) => ({
    name: shortProjectName(p.project_name),
    active: Math.round(p.active_time_seconds / 60),
    idle: Math.round(
      (p.wall_time_seconds - p.active_time_seconds) / 60
    ),
  }));

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="mb-3 text-sm font-medium text-muted-foreground">
        Active Time by Project (top 15)
      </h2>
      <ResponsiveContainer width="100%" height={Math.max(chartData.length * 28, 120)}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
          <XAxis
            type="number"
            tick={{ fontSize: 10 }}
            tickFormatter={(v) => `${v}m`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 10 }}
            width={160}
          />
          <Tooltip
            cursor={false}
            formatter={(value, name) => [
              formatDuration(Number(value) * 60),
              name === "active" ? "Active" : "Idle",
            ]}
          />
          <Bar
            dataKey="active"
            stackId="1"
            fill={c1}
            name="Active"
          />
          <Bar
            dataKey="idle"
            stackId="1"
            fill={c2}
            fillOpacity={0.3}
            name="Idle"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

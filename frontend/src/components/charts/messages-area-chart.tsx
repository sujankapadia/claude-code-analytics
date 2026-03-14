import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DailyStats } from "@/api/types";
import { getChartColors } from "@/lib/format";

export function MessagesAreaChart({ data }: { data: DailyStats[] }) {
  const [c1] = getChartColors();

  const chartData = data
    .slice()
    .reverse()
    .map((d) => ({
      date: d.date.slice(5),
      messages: d.messages,
    }));

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="mb-3 text-sm font-medium text-muted-foreground">
        Daily Messages (last 30 days)
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData}>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 10 }} width={35} />
          <Tooltip labelFormatter={(label) => `Date: ${label}`} />
          <Area
            type="monotone"
            dataKey="messages"
            stroke={c1}
            fill={c1}
            fillOpacity={0.3}
            name="Messages"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

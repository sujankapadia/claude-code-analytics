import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { DailyStats } from "@/api/types";
import { formatNumber, getChartColors } from "@/lib/format";

export function TokenAreaChart({ data }: { data: DailyStats[] }) {
  const [c1, c2] = getChartColors();

  const chartData = data
    .slice()
    .reverse()
    .map((d) => ({
      date: d.date.slice(5), // "MM-DD"
      input: d.input_tokens,
      output: d.output_tokens,
    }));

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="mb-3 text-sm font-medium text-muted-foreground">
        Token Usage (last 30 days)
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData}>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber} width={45} />
          <Tooltip
            formatter={(value) => formatNumber(Number(value))}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <Area
            type="monotone"
            dataKey="input"
            stackId="1"
            stroke={c1}
            fill={c1}
            fillOpacity={0.4}
            name="Input Tokens"
          />
          <Area
            type="monotone"
            dataKey="output"
            stackId="1"
            stroke={c2}
            fill={c2}
            fillOpacity={0.4}
            name="Output Tokens"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

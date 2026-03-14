import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { TokenTimelinePoint } from "@/api/types";
import { formatNumber, getChartColors } from "@/lib/format";

export function TokenTimelineChart({
  data,
}: {
  data: TokenTimelinePoint[];
}) {
  const [c1, c2, c3] = getChartColors();

  const chartData = data.map((p, i) => ({
    index: i,
    timestamp: new Date(p.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    cumulative: p.cumulative_tokens,
    input: p.input_tokens,
    output: p.output_tokens,
  }));

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="mb-3 text-sm font-medium text-muted-foreground">
        Token Timeline
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <XAxis
            dataKey="timestamp"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber} width={45} />
          <Tooltip
            formatter={(value) => formatNumber(Number(value))}
          />
          <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <Line
            type="monotone"
            dataKey="cumulative"
            stroke={c1}
            dot={false}
            name="Cumulative"
          />
          <Line
            type="monotone"
            dataKey="input"
            stroke={c3}
            dot={false}
            strokeDasharray="4 2"
            name="Input"
          />
          <Line
            type="monotone"
            dataKey="output"
            stroke={c2}
            dot={false}
            strokeDasharray="4 2"
            name="Output"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

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

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainingMins = minutes % 60;
  return remainingMins > 0 ? `${hours}h ${remainingMins}m` : `${hours}h`;
}

export function TokenTimelineChart({
  data,
}: {
  data: TokenTimelinePoint[];
}) {
  const [c1, c2, c3] = getChartColors();

  if (data.length === 0) {
    return null;
  }

  const startTime = new Date(data[0].timestamp).getTime();

  let cumInput = 0;
  let cumOutput = 0;
  const chartData = data.map((p, i) => {
    cumInput += p.input_tokens;
    cumOutput += p.output_tokens;
    const elapsedMs = new Date(p.timestamp).getTime() - startTime;
    return {
      index: i,
      elapsed: elapsedMs,
      elapsedLabel: formatElapsed(elapsedMs),
      cumulative: p.cumulative_tokens,
      input: cumInput,
      output: cumOutput,
    };
  });

  return (
    <div className="rounded-lg border bg-card p-4">
      <h2 className="mb-3 text-sm font-medium text-muted-foreground">
        Token Timeline
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <XAxis
            dataKey="elapsed"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
            tickFormatter={(ms) => formatElapsed(ms)}
          />
          <YAxis tick={{ fontSize: 10 }} tickFormatter={formatNumber} width={45} />
          <Tooltip
            formatter={(value) => formatNumber(Number(value))}
            labelFormatter={(ms) => formatElapsed(Number(ms))}
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

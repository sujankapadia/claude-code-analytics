import { Fragment, useMemo } from "react";
import type { HeatmapCell } from "@/api/types";
import { cn } from "@/lib/utils";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

interface ActivityHeatmapProps {
  data: HeatmapCell[];
  className?: string;
}

export function ActivityHeatmap({ data, className }: ActivityHeatmapProps) {
  const { grid, maxCount } = useMemo(() => {
    // Build 7x24 grid
    const g: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0));
    let max = 0;
    for (const cell of data) {
      g[cell.day_of_week][cell.hour] = cell.message_count;
      if (cell.message_count > max) max = cell.message_count;
    }
    return { grid: g, maxCount: max };
  }, [data]);

  if (maxCount === 0) {
    return <p className="text-sm text-muted-foreground">No activity data</p>;
  }

  return (
    <div className={cn("overflow-x-auto", className)}>
      <div className="inline-grid gap-px" style={{ gridTemplateColumns: `auto repeat(24, 1fr)` }}>
        {/* Hour labels */}
        <div />
        {HOURS.map((h) => (
          <div
            key={h}
            className="text-center text-[10px] text-muted-foreground"
          >
            {h % 6 === 0 ? `${h}` : ""}
          </div>
        ))}

        {/* Rows */}
        {DAYS.map((day, dayIdx) => (
          <Fragment key={dayIdx}>
            <div
              className="pr-2 text-right text-[10px] text-muted-foreground leading-[14px]"
            >
              {dayIdx % 2 === 1 ? day : ""}
            </div>
            {HOURS.map((hour) => {
              const count = grid[dayIdx][hour];
              const intensity = maxCount > 0 ? count / maxCount : 0;
              return (
                <div
                  key={`${dayIdx}-${hour}`}
                  className="size-[14px] rounded-sm"
                  style={{
                    backgroundColor:
                      count === 0
                        ? "hsl(var(--muted))"
                        : `color-mix(in srgb, hsl(142 70% 45%) ${20 + intensity * 80}%, transparent)`,
                  }}
                  title={`${day} ${hour}:00 — ${count} messages`}
                />
              );
            })}
          </Fragment>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
        <span>Less</span>
        {[0, 0.25, 0.5, 0.75, 1].map((level) => (
          <div
            key={level}
            className="size-[10px] rounded-sm"
            style={{
              backgroundColor:
                level === 0
                  ? "hsl(var(--muted))"
                  : `color-mix(in srgb, hsl(142 70% 45%) ${20 + level * 80}%, transparent)`,
            }}
          />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}

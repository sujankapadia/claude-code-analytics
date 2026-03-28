import { useCallback } from "react";
import { cn } from "@/lib/utils";

interface ScrollProgressProps {
  /** 0–1 ratio of scroll position. */
  progress: number;
  /** Total message count for label. */
  messageCount: number;
  /** Called with a 0–1 ratio when the user seeks. */
  onSeek: (ratio: number) => void;
  className?: string;
}

export function ScrollProgress({
  progress,
  messageCount,
  onSeek,
  className,
}: ScrollProgressProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onSeek(Number(e.target.value) / 100);
    },
    [onSeek]
  );

  if (messageCount === 0) return null;

  const percent = Math.round(progress * 100);

  return (
    <div className={cn("border-t px-4 py-1.5", className)}>
      <div className="flex items-center gap-2">
        <input
          type="range"
          aria-label="Conversation scroll position"
          aria-valuetext={`${percent}% through conversation`}
          min={0}
          max={100}
          value={percent}
          onChange={handleChange}
          className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-muted accent-primary
            [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary
            [&::-moz-range-thumb]:h-3 [&::-moz-range-thumb]:w-3 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-primary"
        />
        <span className="text-[10px] tabular-nums text-muted-foreground w-7 text-right">
          {percent}%
        </span>
      </div>
    </div>
  );
}

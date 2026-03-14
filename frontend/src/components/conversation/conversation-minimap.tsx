import { useCallback, useRef } from "react";
import type { Message } from "@/api/types";
import { cn } from "@/lib/utils";

interface MinimapProps {
  messages: Message[];
  toolCountByIndex: Map<number, number>;
  /** Currently visible range of message indices. */
  visibleRange: [number, number];
  /** Callback when a minimap region is clicked. */
  onJump: (messageIndex: number) => void;
  className?: string;
}

export function ConversationMinimap({
  messages,
  toolCountByIndex,
  visibleRange,
  onJump,
  className,
}: MinimapProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const ratio = (e.clientY - rect.top) / rect.height;
      const idx = Math.floor(ratio * messages.length);
      onJump(Math.max(0, Math.min(idx, messages.length - 1)));
    },
    [messages.length, onJump]
  );

  if (messages.length === 0) return null;

  // Compute viewport indicator position
  const viewportTop = (visibleRange[0] / messages.length) * 100;
  const viewportHeight =
    ((visibleRange[1] - visibleRange[0] + 1) / messages.length) * 100;

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative cursor-pointer select-none rounded border bg-card",
        className
      )}
      onClick={handleClick}
      title="Click to jump"
    >
      {/* Message density bars */}
      <div className="flex h-full flex-col">
        {messages.map((msg) => {
          const toolCount = toolCountByIndex.get(msg.message_index) ?? 0;
          const isUser = msg.role === "user";
          // Height based on content length (clamped)
          const contentLen = msg.content?.length ?? 0;
          const barHeight = Math.max(1, Math.min(4, Math.ceil(contentLen / 200)));

          return (
            <div
              key={msg.message_id}
              className="flex items-center gap-px px-0.5"
              style={{ height: `${barHeight}px`, minHeight: "1px" }}
            >
              <div
                className={cn(
                  "h-full flex-1 rounded-sm",
                  isUser ? "bg-blue-500/60" : "bg-green-500/60"
                )}
              />
              {toolCount > 0 && (
                <div
                  className="h-full rounded-sm bg-amber-500/60"
                  style={{ width: `${Math.min(toolCount * 2, 8)}px` }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Viewport indicator */}
      <div
        className="absolute inset-x-0 rounded border border-foreground/30 bg-foreground/10 pointer-events-none"
        style={{
          top: `${viewportTop}%`,
          height: `${Math.max(viewportHeight, 2)}%`,
        }}
      />
    </div>
  );
}

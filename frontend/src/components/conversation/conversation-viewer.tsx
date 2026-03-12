import { useMemo, useRef, useState, useCallback, useEffect } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Search, X } from "lucide-react";
import type { Message, ToolUse, TokenUsage } from "@/api/types";
import { ConversationMessage } from "./conversation-message";
import { ConversationMinimap } from "./conversation-minimap";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface ConversationViewerProps {
  messages: Message[];
  toolUses: ToolUse[];
  tokens?: TokenUsage;
  /** Initial message index to scroll to (from URL hash). */
  initialIndex?: number;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

export function ConversationViewer({
  messages,
  toolUses,
  tokens,
  initialIndex,
}: ConversationViewerProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [currentMatch, setCurrentMatch] = useState(0);

  // Group tool uses by message_index
  const toolsByMessage = useMemo(() => {
    const map = new Map<number, ToolUse[]>();
    for (const tool of toolUses) {
      const existing = map.get(tool.message_index) ?? [];
      existing.push(tool);
      map.set(tool.message_index, existing);
    }
    return map;
  }, [toolUses]);

  // Tool count by message_index for minimap
  const toolCountByIndex = useMemo(() => {
    const map = new Map<number, number>();
    for (const [idx, tools] of toolsByMessage) {
      map.set(idx, tools.length);
    }
    return map;
  }, [toolsByMessage]);

  // Search matches
  const searchMatches = useMemo(() => {
    if (!searchQuery || searchQuery.length < 2) return [];
    const q = searchQuery.toLowerCase();
    const matches: number[] = [];
    messages.forEach((msg, i) => {
      if (msg.content?.toLowerCase().includes(q)) {
        matches.push(i);
      }
    });
    return matches;
  }, [messages, searchQuery]);

  // Estimate row height based on content
  const estimateSize = useCallback(
    (index: number) => {
      const msg = messages[index];
      const contentLen = msg.content?.length ?? 0;
      const toolCount = toolsByMessage.get(msg.message_index)?.length ?? 0;
      // Base height (header) + content lines + tool cards
      const contentLines = Math.ceil(contentLen / 80);
      return 60 + contentLines * 20 + toolCount * 40;
    },
    [messages, toolsByMessage]
  );

  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize,
    overscan: 5,
  });

  // Visible range for minimap
  const virtualItems = virtualizer.getVirtualItems();
  const visibleRange: [number, number] = virtualItems.length > 0
    ? [virtualItems[0].index, virtualItems[virtualItems.length - 1].index]
    : [0, 0];

  // Scroll to initial index
  useEffect(() => {
    if (initialIndex != null && initialIndex >= 0 && initialIndex < messages.length) {
      virtualizer.scrollToIndex(initialIndex, { align: "start" });
    }
  }, [initialIndex, messages.length, virtualizer]);

  // Jump to message from minimap
  const handleMinimapJump = useCallback(
    (index: number) => {
      virtualizer.scrollToIndex(index, { align: "start" });
    },
    [virtualizer]
  );

  // Navigate search matches
  const jumpToMatch = useCallback(
    (matchIdx: number) => {
      if (searchMatches.length === 0) return;
      const wrapped = ((matchIdx % searchMatches.length) + searchMatches.length) % searchMatches.length;
      setCurrentMatch(wrapped);
      virtualizer.scrollToIndex(searchMatches[wrapped], { align: "center" });
    },
    [searchMatches, virtualizer]
  );

  // Keyboard shortcut for search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "f") {
        e.preventDefault();
        setSearchOpen(true);
      }
      if (e.key === "Escape" && searchOpen) {
        setSearchOpen(false);
        setSearchQuery("");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [searchOpen]);

  const totalTokens = tokens
    ? tokens.input_tokens + tokens.output_tokens
    : 0;
  const inputRatio = tokens && totalTokens > 0
    ? (tokens.input_tokens / totalTokens) * 100
    : 0;

  return (
    <div className="flex h-[calc(100vh-14rem)] gap-2">
      {/* Minimap */}
      <ConversationMinimap
        messages={messages}
        toolCountByIndex={toolCountByIndex}
        visibleRange={visibleRange}
        onJump={handleMinimapJump}
        className="hidden w-10 shrink-0 lg:block"
      />

      {/* Main conversation area */}
      <div className="flex flex-1 flex-col overflow-hidden rounded-lg border">
        {/* Search bar */}
        {searchOpen && (
          <div className="flex items-center gap-2 border-b bg-card px-3 py-2">
            <Search className="size-4 text-muted-foreground" />
            <Input
              autoFocus
              placeholder="Search in conversation..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentMatch(0);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  jumpToMatch(e.shiftKey ? currentMatch - 1 : currentMatch + 1);
                }
              }}
              className="h-7 flex-1 border-0 bg-transparent text-sm shadow-none focus-visible:ring-0"
            />
            {searchMatches.length > 0 && (
              <span className="text-xs text-muted-foreground">
                {currentMatch + 1}/{searchMatches.length}
              </span>
            )}
            <button
              onClick={() => {
                setSearchOpen(false);
                setSearchQuery("");
              }}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between border-b px-4 py-2">
          <span className="text-sm font-medium">
            {messages.length} messages
          </span>
          <div className="flex items-center gap-2">
            {!searchOpen && (
              <button
                onClick={() => setSearchOpen(true)}
                className="text-muted-foreground hover:text-foreground"
                title="Search (Cmd+F)"
              >
                <Search className="size-4" />
              </button>
            )}
          </div>
        </div>

        {/* Virtualized message list */}
        <div ref={parentRef} className="flex-1 overflow-auto">
          <div
            className="relative w-full"
            style={{ height: `${virtualizer.getTotalSize()}px` }}
          >
            {virtualItems.map((virtualRow) => {
              const msg = messages[virtualRow.index];
              const tools = toolsByMessage.get(msg.message_index) ?? [];
              const isSearchMatch = searchMatches.includes(virtualRow.index);

              return (
                <div
                  key={virtualRow.key}
                  data-index={virtualRow.index}
                  ref={virtualizer.measureElement}
                  className={cn(
                    "absolute left-0 top-0 w-full",
                    isSearchMatch && "ring-2 ring-inset ring-yellow-500/50"
                  )}
                  style={{
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  <ConversationMessage
                    message={msg}
                    tools={tools}
                    index={virtualRow.index}
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* Token usage bar */}
        {tokens && totalTokens > 0 && (
          <div className="border-t px-4 py-2">
            <div className="flex items-center gap-3 text-xs">
              <span className="text-muted-foreground">Tokens:</span>
              <div className="flex h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="bg-blue-500 transition-all"
                  style={{ width: `${inputRatio}%` }}
                  title={`Input: ${formatTokens(tokens.input_tokens)}`}
                />
                <div
                  className="bg-green-500 transition-all"
                  style={{ width: `${100 - inputRatio}%` }}
                  title={`Output: ${formatTokens(tokens.output_tokens)}`}
                />
              </div>
              <span className="tabular-nums text-muted-foreground">
                {formatTokens(tokens.input_tokens)} in / {formatTokens(tokens.output_tokens)} out
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

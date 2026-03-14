import { User, Bot, Bookmark, BookmarkCheck } from "lucide-react";
import type { Message, ToolUse, Bookmark as BookmarkType } from "@/api/types";
import { ToolCallCard } from "./tool-call-card";
import { cn } from "@/lib/utils";

function formatTime(ts: string): string {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

interface ConversationMessageProps {
  message: Message;
  tools: ToolUse[];
  /** Index used for deep linking / scroll-to */
  index: number;
  /** Existing bookmark for this message, if any */
  bookmark?: BookmarkType;
  /** Called when user wants to add/remove a bookmark */
  onBookmarkToggle?: (messageIndex: number, existing?: BookmarkType) => void;
}

export function ConversationMessage({
  message,
  tools,
  index,
  bookmark,
  onBookmarkToggle,
}: ConversationMessageProps) {
  const isUser = message.role === "user";
  const tokens =
    (message.input_tokens ?? 0) + (message.output_tokens ?? 0);

  return (
    <div
      id={`msg-${index}`}
      className={cn(
        "group px-4 py-3",
        isUser ? "bg-background" : "bg-muted/30"
      )}
    >
      {/* Header */}
      <div className="mb-1.5 flex items-center gap-2">
        {isUser ? (
          <User className="size-4 text-blue-500" />
        ) : (
          <Bot className="size-4 text-green-500" />
        )}
        <span
          className={cn(
            "text-xs font-semibold",
            isUser ? "text-blue-500" : "text-green-500"
          )}
        >
          {isUser ? "User" : "Assistant"}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatTime(message.timestamp)}
        </span>

        {/* Bookmark indicator */}
        {bookmark && (
          <span className="text-xs text-amber-500 font-medium truncate max-w-[200px]" title={bookmark.name}>
            {bookmark.name}
          </span>
        )}

        <span className="ml-auto flex items-center gap-2">
          {/* Bookmark button — visible on hover or when bookmarked */}
          {onBookmarkToggle && (
            <button
              onClick={() => onBookmarkToggle(message.message_index, bookmark)}
              className={cn(
                "transition-opacity",
                bookmark
                  ? "text-amber-500 opacity-100"
                  : "text-muted-foreground opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-amber-500"
              )}
              aria-label={bookmark ? "Edit bookmark" : "Bookmark this message"}
              title={bookmark ? "Edit bookmark" : "Bookmark this message"}
            >
              {bookmark ? (
                <BookmarkCheck className="size-4" />
              ) : (
                <Bookmark className="size-4" />
              )}
            </button>
          )}
          {tokens > 0 && (
            <span className="text-xs text-muted-foreground">
              {formatTokens(tokens)} tokens
            </span>
          )}
        </span>
      </div>

      {/* Content */}
      {message.content && (
        <div className="pl-6 text-sm whitespace-pre-wrap leading-relaxed">
          {message.content}
        </div>
      )}

      {/* Tool uses */}
      {tools.length > 0 && (
        <div className="mt-2 space-y-1.5 pl-6">
          {tools.map((tool) => (
            <ToolCallCard key={tool.tool_use_id} tool={tool} />
          ))}
        </div>
      )}
    </div>
  );
}

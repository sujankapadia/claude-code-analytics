import { User, Bot } from "lucide-react";
import type { Message, ToolUse } from "@/api/types";
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
}

export function ConversationMessage({
  message,
  tools,
  index,
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
        {tokens > 0 && (
          <span className="ml-auto text-xs text-muted-foreground">
            {formatTokens(tokens)} tokens
          </span>
        )}
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

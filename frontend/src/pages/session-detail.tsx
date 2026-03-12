import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import {
  fetchSession,
  fetchSessionMessages,
  fetchSessionTokens,
  fetchSessionActivity,
  fetchSessionTextVolume,
} from "@/api/client";
import { ScrollArea } from "@/components/ui/scroll-area";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: session } = useQuery({
    queryKey: ["session", id],
    queryFn: () => fetchSession(id!),
    enabled: !!id,
  });

  const { data: messages, isPending: msgsLoading } = useQuery({
    queryKey: ["session", id, "messages"],
    queryFn: () => fetchSessionMessages(id!),
    enabled: !!id,
  });

  const { data: tokens } = useQuery({
    queryKey: ["session", id, "tokens"],
    queryFn: () => fetchSessionTokens(id!),
    enabled: !!id,
  });

  const { data: activity } = useQuery({
    queryKey: ["session", id, "activity"],
    queryFn: () => fetchSessionActivity(id!),
    enabled: !!id,
  });

  const { data: textVolume } = useQuery({
    queryKey: ["session", id, "text-volume"],
    queryFn: () => fetchSessionTextVolume(id!),
    enabled: !!id,
  });

  if (!session) {
    return <div className="p-4 text-muted-foreground">Loading session...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/sessions" className="hover:underline">
          Sessions
        </Link>
        <span>/</span>
        <span className="font-mono">{session.session_id.slice(0, 8)}</span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Messages" value={session.message_count} />
        <StatCard label="Tool Uses" value={session.tool_use_count} />
        <StatCard
          label="Tokens"
          value={tokens ? formatNumber(tokens.input_tokens + tokens.output_tokens) : "—"}
        />
        <StatCard
          label="Active Time"
          value={
            activity
              ? `${Math.round(activity.active_time_seconds / 60)}m`
              : "—"
          }
        />
      </div>

      {/* Text volume */}
      {textVolume && (
        <div className="rounded-lg border bg-card p-4">
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">Text Volume</h3>
          <div className="flex gap-6 text-sm">
            <span>User: {formatNumber(textVolume.user_text_chars)} chars</span>
            <span>Assistant: {formatNumber(textVolume.assistant_text_chars)} chars</span>
            <span>Tool Output: {formatNumber(textVolume.tool_output_chars)} chars</span>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="rounded-lg border">
        <div className="border-b px-4 py-3">
          <h2 className="text-sm font-medium">
            Conversation {messages ? `(${messages.length} messages)` : ""}
          </h2>
        </div>
        {msgsLoading ? (
          <div className="p-4 text-muted-foreground">Loading messages...</div>
        ) : (
          <ScrollArea className="h-[60vh]">
            <div className="divide-y">
              {messages?.map((msg) => (
                <div key={msg.message_id} className="px-4 py-3">
                  <div className="mb-1 flex items-center gap-2">
                    <span
                      className={`text-xs font-semibold ${
                        msg.role === "user" ? "text-blue-500" : "text-green-500"
                      }`}
                    >
                      {msg.role}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm">
                    {msg.content
                      ? msg.content.length > 500
                        ? msg.content.slice(0, 500) + "..."
                        : msg.content
                      : "—"}
                  </p>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

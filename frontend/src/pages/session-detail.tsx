import { useQuery } from "@tanstack/react-query";
import { useParams, useLocation, Link } from "react-router-dom";
import {
  fetchSession,
  fetchSessionMessages,
  fetchSessionToolUses,
  fetchSessionTokens,
  fetchSessionActivity,
  fetchSessionTextVolume,
  fetchSessionTokenTimeline,
} from "@/api/client";
import { ConversationViewer } from "@/components/conversation/conversation-viewer";
import { TokenTimelineChart } from "@/components/charts/token-timeline-chart";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber } from "@/lib/format";

export default function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();

  // Parse #msg-N from URL hash for deep linking
  const initialIndex = (() => {
    const match = location.hash.match(/^#msg-(\d+)$/);
    return match ? parseInt(match[1], 10) : undefined;
  })();

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

  const { data: toolUses, isPending: toolsLoading } = useQuery({
    queryKey: ["session", id, "tool-uses"],
    queryFn: () => fetchSessionToolUses(id!),
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

  const { data: tokenTimeline } = useQuery({
    queryKey: ["session", id, "token-timeline"],
    queryFn: () => fetchSessionTokenTimeline(id!),
    enabled: !!id,
  });

  if (!session) {
    return <div className="p-4 text-muted-foreground">Loading session...</div>;
  }

  const isLoading = msgsLoading || toolsLoading;

  return (
    <div className="space-y-4">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link to="/sessions" className="hover:underline">
          Sessions
        </Link>
        <span>/</span>
        <span className="font-mono">{session.session_id.slice(0, 8)}</span>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Messages" value={session.message_count} />
        <StatCard label="Tool Uses" value={session.tool_use_count} />
        <StatCard
          label="Tokens"
          value={
            tokens
              ? formatNumber(tokens.input_tokens + tokens.output_tokens)
              : "—"
          }
        />
        <StatCard
          label="Active Time"
          value={
            activity
              ? `${Math.round(activity.active_time_seconds / 60)}m`
              : "—"
          }
        />
        {textVolume && (
          <>
            <StatCard
              label="User Text"
              value={formatNumber(textVolume.user_text_chars) + " chars"}
            />
            <StatCard
              label="Assistant Text"
              value={formatNumber(textVolume.assistant_text_chars) + " chars"}
            />
          </>
        )}
      </div>

      {/* Token timeline chart */}
      {tokenTimeline && tokenTimeline.length > 1 && (
        <TokenTimelineChart data={tokenTimeline} />
      )}

      {/* Conversation Viewer */}
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-[60vh] w-full" />
        </div>
      ) : messages && toolUses ? (
        <ConversationViewer
          messages={messages}
          toolUses={toolUses}
          tokens={tokens}
          initialIndex={initialIndex}
          sessionId={id}
        />
      ) : null}
    </div>
  );
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}

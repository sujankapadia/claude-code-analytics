import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  fetchSessions,
  fetchProjects,
  fetchSessionTokens,
  fetchSessionActivity,
  fetchSessionToolUses,
} from "@/api/client";
import type { SessionSummary } from "@/api/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

function formatDateShort(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export default function SessionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const projectId = searchParams.get("project_id") ?? undefined;
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  const { data: sessions, isPending } = useQuery({
    queryKey: ["sessions", { project_id: projectId }],
    queryFn: () => fetchSessions({ project_id: projectId }),
  });

  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: sessions?.length ?? 0,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 72,
    overscan: 10,
  });

  const selectedSession = useMemo(
    () => sessions?.find((s) => s.session_id === selectedId) ?? null,
    [sessions, selectedId],
  );

  return (
    <div className="flex h-[calc(100vh-5rem)] gap-4">
      {/* Left panel: filter + session list */}
      <div className="flex w-80 shrink-0 flex-col rounded-lg border lg:w-96">
        {/* Filter bar */}
        <div className="flex items-center gap-2 border-b p-3">
          <Select
            value={projectId ?? "all"}
            onValueChange={(v) => {
              if (v === "all") {
                setSearchParams({});
              } else {
                setSearchParams({ project_id: v });
              }
              setSelectedId(null);
            }}
          >
            <SelectTrigger className="h-8 flex-1 text-xs">
              <SelectValue placeholder="All projects" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All projects</SelectItem>
              {projects?.map((p) => (
                <SelectItem key={p.project_id} value={p.project_id}>
                  {p.project_name.split("/").pop()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="shrink-0 text-xs text-muted-foreground">
            {sessions?.length ?? 0} sessions
          </span>
        </div>

        {/* Virtual session list */}
        {isPending ? (
          <div className="space-y-1 p-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-16 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : (
          <div ref={parentRef} className="flex-1 overflow-auto">
            <div
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                position: "relative",
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const s = sessions![virtualRow.index];
                const shortProject = s.project_name.split("/").pop();
                const isSelected = s.session_id === selectedId;
                return (
                  <div
                    key={s.session_id}
                    data-index={virtualRow.index}
                    ref={rowVirtualizer.measureElement}
                    className={cn(
                      "absolute left-0 right-0 cursor-pointer border-b px-3 py-2 transition-colors hover:bg-muted/50",
                      isSelected && "bg-muted",
                    )}
                    style={{ top: virtualRow.start }}
                    onClick={() => setSelectedId(s.session_id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") setSelectedId(s.session_id);
                    }}
                    tabIndex={0}
                    role="button"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm font-medium">
                        {s.session_id.slice(0, 8)}
                      </span>
                      <span className="text-[10px] text-muted-foreground">
                        {formatDateShort(s.start_time)}
                      </span>
                    </div>
                    <div className="mt-0.5 flex items-center justify-between text-xs text-muted-foreground">
                      <span className="truncate">{shortProject}</span>
                      <span className="shrink-0 ml-2">
                        {s.message_count} msgs · {formatDuration(s.duration_seconds)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Right panel: preview pane */}
      <div className="flex-1 overflow-auto rounded-lg border">
        {selectedSession ? (
          <SessionPreview session={selectedSession} />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <p className="text-sm">Select a session to preview</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SessionPreview({ session }: { session: SessionSummary }) {
  const { data: tokens } = useQuery({
    queryKey: ["session", session.session_id, "tokens"],
    queryFn: () => fetchSessionTokens(session.session_id),
  });

  const { data: activity } = useQuery({
    queryKey: ["session", session.session_id, "activity"],
    queryFn: () => fetchSessionActivity(session.session_id),
  });

  const { data: toolUses } = useQuery({
    queryKey: ["session", session.session_id, "tool-uses"],
    queryFn: () => fetchSessionToolUses(session.session_id),
  });

  const totalTokens = tokens
    ? tokens.input_tokens + tokens.output_tokens
    : null;
  const inputPct =
    totalTokens && totalTokens > 0
      ? (tokens!.input_tokens / totalTokens) * 100
      : 50;

  // Group tools by name and count
  const toolCounts = useMemo(() => {
    if (!toolUses) return [];
    const counts: Record<string, number> = {};
    for (const t of toolUses) {
      counts[t.tool_name] = (counts[t.tool_name] ?? 0) + 1;
    }
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10);
  }, [toolUses]);

  return (
    <div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-mono text-lg font-bold">
            {session.session_id.slice(0, 8)}
          </h2>
          <p className="text-sm text-muted-foreground">
            {session.project_name.split("/").pop()}
          </p>
        </div>
        <Link
          to={`/sessions/${session.session_id}`}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          View Conversation
        </Link>
      </div>

      {/* Timeline bar */}
      {session.start_time && session.end_time && (
        <div>
          <p className="mb-1 text-xs text-muted-foreground">Timeline</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{formatDate(session.start_time)}</span>
            <div className="h-1 flex-1 rounded-full bg-muted overflow-hidden">
              {activity && (
                <div
                  className="h-full rounded-full bg-primary/60"
                  style={{
                    width: `${Math.max(
                      ((1 - activity.idle_ratio) * 100),
                      5,
                    )}%`,
                  }}
                />
              )}
            </div>
            <span>{formatDate(session.end_time)}</span>
          </div>
          <p className="mt-1 text-[10px] text-muted-foreground">
            {formatDuration(session.duration_seconds)} total
            {activity &&
              ` · ${Math.round(activity.active_time_seconds / 60)}m active · ${Math.round(activity.idle_ratio * 100)}% idle`}
          </p>
        </div>
      )}

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MiniStat label="Messages" value={session.message_count.toString()} />
        <MiniStat
          label="User / Assistant"
          value={`${session.user_message_count} / ${session.assistant_message_count}`}
        />
        <MiniStat label="Tool Uses" value={session.tool_use_count.toString()} />
        <MiniStat
          label="Duration"
          value={formatDuration(session.duration_seconds)}
        />
      </div>

      {/* Token breakdown */}
      {tokens && totalTokens !== null && (
        <div>
          <p className="mb-1 text-xs text-muted-foreground">
            Token Breakdown · {formatNumber(totalTokens)} total
          </p>
          <div className="flex h-4 overflow-hidden rounded-full">
            <div
              className="bg-chart-1 transition-all"
              style={{ width: `${inputPct}%` }}
              title={`Input: ${formatNumber(tokens.input_tokens)}`}
            />
            <div
              className="bg-chart-2 transition-all"
              style={{ width: `${100 - inputPct}%` }}
              title={`Output: ${formatNumber(tokens.output_tokens)}`}
            />
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-block size-2 rounded-sm bg-chart-1" />
              Input: {formatNumber(tokens.input_tokens)}
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block size-2 rounded-sm bg-chart-2" />
              Output: {formatNumber(tokens.output_tokens)}
            </span>
          </div>
          {(tokens.cache_read_tokens > 0 ||
            tokens.cache_creation_tokens > 0) && (
            <p className="mt-1 text-[10px] text-muted-foreground">
              Cache: {formatNumber(tokens.cache_read_tokens)} read ·{" "}
              {formatNumber(tokens.cache_creation_tokens)} created
            </p>
          )}
        </div>
      )}

      {/* Tools used */}
      {toolCounts.length > 0 && (
        <div>
          <p className="mb-2 text-xs text-muted-foreground">Tools Used</p>
          <div className="flex flex-wrap gap-1.5">
            {toolCounts.map(([name, count]) => (
              <span
                key={name}
                className="inline-flex items-center gap-1 rounded-full border bg-muted/50 px-2 py-0.5 text-xs"
              >
                <span className="font-mono">{name}</span>
                <span className="text-muted-foreground">×{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-2.5">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold">{value}</p>
    </div>
  );
}

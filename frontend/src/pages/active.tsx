import { useQuery } from "@tanstack/react-query";
import { Activity, Clock, Monitor, Terminal } from "lucide-react";
import { fetchActiveSessions } from "@/api/client";
import type { ActiveSessionInfo, RecentSessionInfo } from "@/api/types";

function formatDuration(minutes: number): string {
  if (minutes < 1) return "<1m";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatTimeAgo(minutes: number): string {
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const h = Math.floor(minutes / 60);
  return `${h}h ${minutes % 60}m ago`;
}

function StatusDot() {
  return (
    <span
      className="inline-block size-2.5 rounded-full bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]"
      title="running"
    />
  );
}

function ActiveCard({ session }: { session: ActiveSessionInfo }) {
  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusDot />
          <h3 className="font-semibold text-base">{session.project_name}</h3>
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          {formatDuration(session.duration_minutes)}
        </span>
      </div>

      {session.recent_messages.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-muted-foreground">Recent messages</p>
          {session.recent_messages.map((msg, i) => (
            <p key={i} className="text-sm leading-relaxed line-clamp-2 border-l-2 border-muted pl-2">
              {msg}
            </p>
          ))}
        </div>
      )}

      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1" title="Terminal">
          <Terminal className="size-3" />
          {session.tty}
        </span>
        <span className="flex items-center gap-1" title="PID">
          <Monitor className="size-3" />
          PID {session.pid}
        </span>
      </div>
    </div>
  );
}

function RecentCard({ session }: { session: RecentSessionInfo }) {
  return (
    <div className="rounded-lg border bg-card/50 p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="inline-block size-2.5 rounded-full bg-muted-foreground/30" />
          <h3 className="font-medium text-sm">{session.project_name}</h3>
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">
          ended {formatTimeAgo(session.ended_minutes_ago)}
        </span>
      </div>

      {session.first_user_message && (
        <p className="text-sm text-muted-foreground line-clamp-2">
          {session.first_user_message}
        </p>
      )}

      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span>{session.message_count} messages</span>
      </div>
    </div>
  );
}

export default function ActivePage() {
  const { data, isPending, error } = useQuery({
    queryKey: ["active-sessions"],
    queryFn: () => fetchActiveSessions({ include_recent: true, recent_minutes: 120 }),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const activeCount = data?.active.length ?? 0;
  const recentCount = data?.recent.length ?? 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Activity className="size-6 text-primary" />
        <h1 className="text-2xl font-bold">Active Sessions</h1>
        {activeCount > 0 && (
          <span className="rounded-full bg-green-500/10 px-2.5 py-0.5 text-xs font-medium text-green-600">
            {activeCount} active
          </span>
        )}
      </div>

      {isPending && (
        <div className="space-y-4">
          {[1, 2].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load active sessions: {error.message}
        </div>
      )}

      {data && (
        <>
          {activeCount === 0 && recentCount === 0 && (
            <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
              <Clock className="mx-auto mb-2 size-8 opacity-50" />
              <p>No active or recent Claude Code sessions detected.</p>
              <p className="text-xs mt-1">
                Start a Claude Code session in a terminal to see it here.
              </p>
            </div>
          )}

          {activeCount > 0 && (
            <section>
              <h2 className="text-sm font-medium text-muted-foreground mb-3">
                Running now
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                {data.active.map((s) => (
                  <ActiveCard key={s.pid} session={s} />
                ))}
              </div>
            </section>
          )}

          {recentCount > 0 && (
            <section>
              <h2 className="text-sm font-medium text-muted-foreground mb-3">
                Recently ended
              </h2>
              <div className="grid gap-3 md:grid-cols-2">
                {data.recent.map((s) => (
                  <RecentCard key={s.session_id} session={s} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

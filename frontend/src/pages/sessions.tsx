import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { fetchSessions } from "@/api/client";

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

export default function SessionsPage() {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project_id") ?? undefined;

  const { data: sessions, isPending } = useQuery({
    queryKey: ["sessions", { project_id: projectId }],
    queryFn: () => fetchSessions({ project_id: projectId }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Sessions</h1>
        {projectId && (
          <Link to="/sessions" className="text-sm text-muted-foreground hover:underline">
            Clear filter
          </Link>
        )}
      </div>

      {isPending ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : (
        <div className="space-y-1">
          {sessions?.map((s) => {
            const shortProject = s.project_name.split("/").pop();
            return (
              <Link
                key={s.session_id}
                to={`/sessions/${s.session_id}`}
                className="flex items-center justify-between rounded-lg border px-4 py-3 transition-colors hover:bg-muted/50"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">
                    {s.session_id.slice(0, 8)}
                    <span className="ml-2 text-xs text-muted-foreground">{shortProject}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(s.start_time)} · {formatDuration(s.duration_seconds)}
                  </p>
                </div>
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span>{s.message_count} msgs</span>
                  <span>{s.tool_use_count} tools</span>
                </div>
              </Link>
            );
          })}
          {sessions?.length === 0 && (
            <p className="py-8 text-center text-muted-foreground">No sessions found.</p>
          )}
        </div>
      )}
    </div>
  );
}

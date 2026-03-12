import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchSearch } from "@/api/client";
import { Input } from "@/components/ui/input";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  const handleChange = (value: string) => {
    setQuery(value);
    if (debounceTimer) clearTimeout(debounceTimer);
    const timer = setTimeout(() => setDebouncedQuery(value), 300);
    setDebounceTimer(timer);
  };

  const { data, isPending, error } = useQuery({
    queryKey: ["search", debouncedQuery],
    queryFn: () => fetchSearch({ q: debouncedQuery, per_page: 5 }),
    enabled: debouncedQuery.length >= 2,
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Search</h1>

      <Input
        placeholder="Search conversations... (FTS5 syntax supported)"
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        className="max-w-lg"
        autoFocus
      />

      {error && (
        <p className="text-sm text-destructive">{(error as Error).message}</p>
      )}

      {isPending && debouncedQuery.length >= 2 && (
        <p className="text-sm text-muted-foreground">Searching...</p>
      )}

      {data && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {data.total_sessions} session{data.total_sessions !== 1 ? "s" : ""} with matches
          </p>

          {Object.entries(data.results_by_session).map(([sessionId, results]) => (
            <div key={sessionId} className="rounded-lg border">
              <div className="border-b bg-muted/30 px-4 py-2">
                <Link
                  to={`/sessions/${sessionId}`}
                  className="font-mono text-sm font-medium hover:underline"
                >
                  {sessionId.slice(0, 8)}
                </Link>
                <span className="ml-2 text-xs text-muted-foreground">
                  {results[0]?.project_name.split("/").pop()} · {results.length} match
                  {results.length !== 1 ? "es" : ""}
                </span>
              </div>
              <div className="divide-y">
                {results.slice(0, 5).map((r, i) => (
                  <div key={i} className="px-4 py-2 text-sm">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="rounded bg-muted px-1.5 py-0.5">{r.result_type}</span>
                      <span>{r.detail}</span>
                      <span>{new Date(r.timestamp).toLocaleString()}</span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-muted-foreground">
                      {r.snippet ? (
                        <span dangerouslySetInnerHTML={{ __html: r.snippet }} />
                      ) : (
                        (r.matched_content ?? "").slice(0, 200)
                      )}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

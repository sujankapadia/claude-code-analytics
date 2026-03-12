import { useState, useEffect, useCallback, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { Search as SearchIcon, ChevronDown, X, Clock } from "lucide-react";
import { fetchSearch, fetchProjects, fetchToolNames } from "@/api/client";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const SCOPES = ["All", "Messages", "Tool Inputs", "Tool Results"] as const;
const HISTORY_KEY = "search_history";
const MAX_HISTORY = 10;

function loadHistory(): string[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveToHistory(q: string) {
  if (!q || q.length < 2) return;
  const history = loadHistory().filter((h) => h !== q);
  history.unshift(q);
  localStorage.setItem(
    HISTORY_KEY,
    JSON.stringify(history.slice(0, MAX_HISTORY))
  );
}

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Filters
  const [scope, setScope] = useState<string>(
    searchParams.get("scope") ?? "All"
  );
  const [projectId, setProjectId] = useState<string>(
    searchParams.get("project_id") ?? ""
  );
  const [toolName, setToolName] = useState<string>(
    searchParams.get("tool_name") ?? ""
  );
  const [filtersOpen, setFiltersOpen] = useState(false);

  // History
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState(loadHistory);

  // Keyboard nav
  const [focusedResult, setFocusedResult] = useState(-1);
  const resultRefs = useRef<(HTMLAnchorElement | null)[]>([]);

  // Filter data
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });
  const { data: toolNames } = useQuery({
    queryKey: ["tool-names"],
    queryFn: fetchToolNames,
  });

  // Debounce search
  const handleChange = useCallback((value: string) => {
    setQuery(value);
    setFocusedResult(-1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedQuery(value), 300);
  }, []);

  // Sync URL params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (debouncedQuery) params.q = debouncedQuery;
    if (scope !== "All") params.scope = scope;
    if (projectId) params.project_id = projectId;
    if (toolName) params.tool_name = toolName;
    setSearchParams(params, { replace: true });
  }, [debouncedQuery, scope, projectId, toolName, setSearchParams]);

  // Save to history on search
  useEffect(() => {
    if (debouncedQuery.length >= 2) {
      saveToHistory(debouncedQuery);
      setHistory(loadHistory());
    }
  }, [debouncedQuery]);

  const { data, isPending, error } = useQuery({
    queryKey: ["search", debouncedQuery, scope, projectId, toolName],
    queryFn: () =>
      fetchSearch({
        q: debouncedQuery,
        scope: scope !== "All" ? scope : undefined,
        project_id: projectId || undefined,
        tool_name: toolName || undefined,
        per_page: 10,
      }),
    enabled: debouncedQuery.length >= 2,
  });

  // Flatten results for keyboard nav
  const flatResults = data
    ? Object.entries(data.results_by_session).flatMap(([sessionId, results]) =>
        results.map((r) => ({ ...r, sessionId }))
      )
    : [];

  // Keyboard handler
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusedResult((prev) =>
          Math.min(prev + 1, flatResults.length - 1)
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedResult((prev) => Math.max(prev - 1, -1));
      } else if (e.key === "Enter" && focusedResult >= 0) {
        e.preventDefault();
        resultRefs.current[focusedResult]?.click();
      }
    },
    [flatResults.length, focusedResult]
  );

  // Scroll focused result into view
  useEffect(() => {
    if (focusedResult >= 0) {
      resultRefs.current[focusedResult]?.scrollIntoView({
        block: "nearest",
      });
    }
  }, [focusedResult]);

  const hasFilters = scope !== "All" || projectId || toolName;
  let resultIdx = 0;

  return (
    <div className="space-y-4" onKeyDown={handleKeyDown}>
      <h1 className="text-2xl font-bold">Search</h1>

      {/* Search input */}
      <div className="relative max-w-2xl">
        <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search conversations... (FTS5 syntax supported)"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          onFocus={() => {
            if (!query && history.length > 0) setHistoryOpen(true);
          }}
          onBlur={() => setTimeout(() => setHistoryOpen(false), 200)}
          className="pl-9 pr-20"
          autoFocus
        />
        <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
          {query && (
            <button
              onClick={() => {
                handleChange("");
                setDebouncedQuery("");
              }}
              className="rounded p-1 text-muted-foreground hover:text-foreground"
            >
              <X className="size-3.5" />
            </button>
          )}
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className={cn(
              "flex items-center gap-1 rounded px-2 py-1 text-xs",
              hasFilters
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Filters
            <ChevronDown
              className={cn(
                "size-3 transition-transform",
                filtersOpen && "rotate-180"
              )}
            />
          </button>
        </div>

        {/* Search history dropdown */}
        {historyOpen && history.length > 0 && (
          <div className="absolute z-10 mt-1 w-full rounded-lg border bg-popover p-1 shadow-md">
            {history.map((h) => (
              <button
                key={h}
                className="flex w-full items-center gap-2 rounded px-3 py-1.5 text-left text-sm hover:bg-muted"
                onMouseDown={() => {
                  handleChange(h);
                  setDebouncedQuery(h);
                  setHistoryOpen(false);
                }}
              >
                <Clock className="size-3.5 text-muted-foreground" />
                {h}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Filters */}
      {filtersOpen && (
        <div className="flex max-w-2xl flex-wrap items-end gap-3 rounded-lg border bg-card p-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Scope</label>
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              className="rounded border bg-background px-2 py-1.5 text-sm"
            >
              {SCOPES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Project</label>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="max-w-48 truncate rounded border bg-background px-2 py-1.5 text-sm"
            >
              <option value="">All projects</option>
              {projects?.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  {p.project_name.split("/").pop()}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Tool</label>
            <select
              value={toolName}
              onChange={(e) => setToolName(e.target.value)}
              className="rounded border bg-background px-2 py-1.5 text-sm"
            >
              <option value="">All tools</option>
              {toolNames?.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          {hasFilters && (
            <button
              onClick={() => {
                setScope("All");
                setProjectId("");
                setToolName("");
              }}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Status */}
      {error && (
        <p className="text-sm text-destructive">{(error as Error).message}</p>
      )}
      {isPending && debouncedQuery.length >= 2 && (
        <p className="text-sm text-muted-foreground">Searching...</p>
      )}

      {/* Results */}
      {data && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {data.total_sessions} session
            {data.total_sessions !== 1 ? "s" : ""} with matches
            {data.has_more && " (showing first page)"}
          </p>

          {Object.entries(data.results_by_session).map(
            ([sessionId, results]) => (
              <div key={sessionId} className="rounded-lg border">
                <div className="border-b bg-muted/30 px-4 py-2">
                  <Link
                    to={`/sessions/${sessionId}`}
                    className="font-mono text-sm font-medium hover:underline"
                  >
                    {sessionId.slice(0, 8)}
                  </Link>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {results[0]?.project_name.split("/").pop()} ·{" "}
                    {results.length} match
                    {results.length !== 1 ? "es" : ""}
                  </span>
                </div>
                <div className="divide-y">
                  {results.map((r, i) => {
                    const idx = resultIdx++;
                    return (
                      <Link
                        key={i}
                        ref={(el) => {
                          resultRefs.current[idx] = el;
                        }}
                        to={`/sessions/${sessionId}#msg-${r.message_index}`}
                        className={cn(
                          "block px-4 py-2 text-sm transition-colors hover:bg-muted/50",
                          focusedResult === idx && "bg-muted/50 ring-2 ring-inset ring-ring/30"
                        )}
                      >
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span className="rounded bg-muted px-1.5 py-0.5">
                            {r.result_type}
                          </span>
                          <span>{r.detail}</span>
                          <span>
                            {new Date(r.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-muted-foreground">
                          {r.snippet ? (
                            <span
                              dangerouslySetInnerHTML={{
                                __html: r.snippet,
                              }}
                            />
                          ) : (
                            (r.matched_content ?? "").slice(0, 200)
                          )}
                        </p>
                      </Link>
                    );
                  })}
                </div>
              </div>
            )
          )}
        </div>
      )}

      {/* Keyboard hint */}
      {flatResults.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Use arrow keys to navigate results, Enter to open
        </p>
      )}
    </div>
  );
}

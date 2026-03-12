import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  BrainCircuit,
  FileText,
  FolderOpen,
  Home,
  Import,
  MessageSquare,
  Search,
} from "lucide-react";
import { fetchProjects, fetchSessions, fetchSearch } from "@/api/client";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface CommandItem {
  id: string;
  label: string;
  sublabel?: string;
  icon: React.ReactNode;
  action: () => void;
  score?: number;
}

/** Fuzzy match: checks if all chars of `pattern` appear in `text` in order.
 *  Returns a score (lower = better) or -1 for no match. */
function fuzzyMatch(text: string, pattern: string): number {
  const t = text.toLowerCase();
  const p = pattern.toLowerCase();
  let ti = 0;
  let pi = 0;
  let score = 0;
  let lastMatchIdx = -1;

  while (ti < t.length && pi < p.length) {
    if (t[ti] === p[pi]) {
      // Bonus for consecutive matches
      const gap = lastMatchIdx >= 0 ? ti - lastMatchIdx - 1 : 0;
      score += gap;
      // Bonus for matching at word boundaries
      if (ti === 0 || t[ti - 1] === " " || t[ti - 1] === "/" || t[ti - 1] === "-") {
        score -= 2;
      }
      lastMatchIdx = ti;
      pi++;
    }
    ti++;
  }

  if (pi < p.length) return -1; // Not all chars matched
  return score;
}

function fuzzyFilter(items: CommandItem[], query: string): CommandItem[] {
  const q = query.trim();
  if (!q) return items;

  const scored: Array<{ item: CommandItem; score: number }> = [];
  for (const item of items) {
    const labelScore = fuzzyMatch(item.label, q);
    const subScore = item.sublabel ? fuzzyMatch(item.sublabel, q) : -1;
    const best = labelScore >= 0 && subScore >= 0
      ? Math.min(labelScore, subScore)
      : Math.max(labelScore, subScore);
    if (best >= 0) {
      scored.push({ item: { ...item, score: best }, score: best });
    }
  }

  scored.sort((a, b) => a.score - b.score);
  return scored.map((s) => s.item);
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
    enabled: open,
  });

  const { data: sessions } = useQuery({
    queryKey: ["sessions", { limit: 50 }],
    queryFn: () => fetchSessions({ limit: 50 }),
    enabled: open,
  });

  // Debounce query for FTS search (250ms)
  useEffect(() => {
    if (query.trim().length < 2) {
      setDebouncedQuery("");
      return;
    }
    const timer = setTimeout(() => setDebouncedQuery(query.trim()), 250);
    return () => clearTimeout(timer);
  }, [query]);

  // FTS backend search
  const { data: searchResults } = useQuery({
    queryKey: ["command-palette-search", debouncedQuery],
    queryFn: () => fetchSearch({ q: debouncedQuery, per_page: 5 }),
    enabled: open && debouncedQuery.length >= 2,
    staleTime: 10_000,
  });

  // Cmd+K to open
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Reset on open
  useEffect(() => {
    if (open) {
      setQuery("");
      setDebouncedQuery("");
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  const go = useCallback(
    (path: string) => {
      navigate(path);
      setOpen(false);
    },
    [navigate],
  );

  const items = useMemo<CommandItem[]>(() => {
    const pages: CommandItem[] = [
      {
        id: "page-dashboard",
        label: "Dashboard",
        icon: <Home className="size-4" />,
        action: () => go("/"),
      },
      {
        id: "page-sessions",
        label: "Sessions",
        icon: <MessageSquare className="size-4" />,
        action: () => go("/sessions"),
      },
      {
        id: "page-search",
        label: "Search",
        icon: <Search className="size-4" />,
        action: () => go("/search"),
      },
      {
        id: "page-analytics",
        label: "Analytics",
        icon: <BarChart3 className="size-4" />,
        action: () => go("/analytics"),
      },
      {
        id: "page-analysis",
        label: "Analysis",
        icon: <BrainCircuit className="size-4" />,
        action: () => go("/analysis"),
      },
      {
        id: "page-import",
        label: "Import",
        icon: <Import className="size-4" />,
        action: () => go("/import"),
      },
    ];

    const projectItems: CommandItem[] = (projects ?? []).map((p) => ({
      id: `project-${p.project_id}`,
      label: p.project_name.split("/").pop() ?? p.project_name,
      sublabel: `${p.total_sessions} sessions · ${p.total_messages} msgs`,
      icon: <FolderOpen className="size-4" />,
      action: () => go(`/sessions?project_id=${p.project_id}`),
    }));

    const sessionItems: CommandItem[] = (sessions ?? []).slice(0, 20).map((s) => ({
      id: `session-${s.session_id}`,
      label: s.session_id.slice(0, 8),
      sublabel: `${s.project_name.split("/").pop()} · ${s.message_count} msgs`,
      icon: <MessageSquare className="size-4" />,
      action: () => go(`/sessions/${s.session_id}`),
    }));

    return [...pages, ...projectItems, ...sessionItems];
  }, [projects, sessions, go]);

  // FTS results as CommandItems
  const ftsItems = useMemo<CommandItem[]>(() => {
    if (!searchResults) return [];
    const results: CommandItem[] = [];
    for (const [sessionId, hits] of Object.entries(searchResults.results_by_session)) {
      for (const hit of hits.slice(0, 2)) {
        const snippet = hit.snippet
          ? hit.snippet.slice(0, 80) + (hit.snippet.length > 80 ? "..." : "")
          : hit.matched_content.slice(0, 80);
        results.push({
          id: `fts-${sessionId}-${hit.message_index}`,
          label: snippet,
          sublabel: `${hit.project_name.split("/").pop()} · ${hit.result_type}`,
          icon: <FileText className="size-4" />,
          action: () => go(`/sessions/${sessionId}#msg-${hit.message_index}`),
        });
      }
      if (results.length >= 5) break;
    }
    return results;
  }, [searchResults, go]);

  const filtered = useMemo(() => {
    const localResults = fuzzyFilter(items, query);
    if (ftsItems.length === 0) return localResults;
    // Combine: local results first, then FTS results (deduplicated)
    const ftsIds = new Set(ftsItems.map((f) => f.id));
    const combined = localResults.filter((r) => !ftsIds.has(r.id));
    return [...combined, ...ftsItems];
  }, [items, ftsItems, query]);

  // Clamp selection
  useEffect(() => {
    setSelectedIdx((i) => Math.min(i, Math.max(filtered.length - 1, 0)));
  }, [filtered.length]);

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.children[selectedIdx] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIdx]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && filtered[selectedIdx]) {
      e.preventDefault();
      filtered[selectedIdx].action();
    }
  };

  const hasFts = ftsItems.length > 0;
  const localCount = filtered.length - ftsItems.length;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg gap-0 overflow-hidden p-0">
        <DialogTitle className="sr-only">Command Palette</DialogTitle>
        <div className="flex items-center border-b px-3">
          <Search className="mr-2 size-4 shrink-0 text-muted-foreground" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIdx(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a command or search..."
            className="flex-1 bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="ml-2 shrink-0 rounded border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
            ESC
          </kbd>
        </div>
        <div ref={listRef} className="max-h-80 overflow-auto p-1">
          {filtered.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </p>
          )}
          {filtered.map((item, i) => {
            // Show separator before FTS results
            const isFtsStart = hasFts && i === localCount;
            return (
              <div key={item.id}>
                {isFtsStart && (
                  <div className="px-3 pb-1 pt-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Content matches
                  </div>
                )}
                <button
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm",
                    i === selectedIdx
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted/50",
                  )}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIdx(i)}
                >
                  <span className="shrink-0 text-muted-foreground">
                    {item.icon}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">
                      {item.label}
                    </span>
                    {item.sublabel && (
                      <span className="block truncate text-xs text-muted-foreground">
                        {item.sublabel}
                      </span>
                    )}
                  </span>
                </button>
              </div>
            );
          })}
        </div>
        <div className="border-t px-3 py-2 text-[10px] text-muted-foreground">
          <kbd className="rounded border bg-muted px-1">↑↓</kbd> navigate{" "}
          <kbd className="ml-2 rounded border bg-muted px-1">↵</kbd> select{" "}
          <kbd className="ml-2 rounded border bg-muted px-1">esc</kbd> close
        </div>
      </DialogContent>
    </Dialog>
  );
}

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bookmark,
  FolderOpen,
  MessageSquare,
  Search,
} from "lucide-react";
import { fetchProjects, fetchSessions, fetchBookmarks } from "@/api/client";
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
  group: "project" | "session" | "bookmark";
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

const GROUP_LABELS: Record<string, string> = {
  project: "Projects",
  bookmark: "Bookmarks",
  session: "Sessions",
};

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
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

  const { data: bookmarks } = useQuery({
    queryKey: ["bookmarks"],
    queryFn: () => fetchBookmarks(),
    enabled: open,
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
    const projectItems: CommandItem[] = (projects ?? []).map((p) => ({
      id: `project-${p.project_id}`,
      label: p.project_name.split("/").pop() ?? p.project_name,
      sublabel: `${p.total_sessions} sessions · ${p.total_messages} msgs`,
      icon: <FolderOpen className="size-4" />,
      group: "project" as const,
      action: () => go(`/sessions?project_id=${p.project_id}`),
    }));

    const bookmarkItems: CommandItem[] = (bookmarks ?? []).map((b) => ({
      id: `bookmark-${b.bookmark_id}`,
      label: b.name,
      sublabel: b.description || (b.project_name ? `${b.project_name.split("/").pop()}` : undefined),
      icon: <Bookmark className="size-4" />,
      group: "bookmark" as const,
      action: () => go(`/sessions/${b.session_id}#msg-${b.message_index}`),
    }));

    const sessionItems: CommandItem[] = (sessions ?? []).slice(0, 20).map((s) => ({
      id: `session-${s.session_id}`,
      label: s.session_id.slice(0, 8),
      sublabel: `${s.project_name.split("/").pop()} · ${s.message_count} msgs`,
      icon: <MessageSquare className="size-4" />,
      group: "session" as const,
      action: () => go(`/sessions/${s.session_id}`),
    }));

    return [...projectItems, ...bookmarkItems, ...sessionItems];
  }, [projects, sessions, bookmarks, go]);

  const filtered = useMemo(() => fuzzyFilter(items, query), [items, query]);

  // Clamp selection
  useEffect(() => {
    setSelectedIdx((i) => Math.min(i, Math.max(filtered.length - 1, 0)));
  }, [filtered.length]);

  // Scroll selected into view
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${selectedIdx}"]`) as HTMLElement | undefined;
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
            placeholder="Search projects, bookmarks, sessions..."
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
            const prevGroup = i > 0 ? filtered[i - 1].group : null;
            const showHeader = item.group !== prevGroup;
            return (
              <div key={item.id} data-idx={i}>
                {showHeader && (
                  <div className="px-3 pb-1 pt-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    {GROUP_LABELS[item.group]}
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

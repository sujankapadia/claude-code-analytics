import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Trash2, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchBookmarks, deleteBookmark } from "@/api/client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function BookmarksPage() {
  const queryClient = useQueryClient();

  const { data: bookmarks, isPending, error } = useQuery({
    queryKey: ["bookmarks"],
    queryFn: () => fetchBookmarks(),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBookmark,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bookmarks"] });
    },
  });

  // Group bookmarks by project
  const grouped = (bookmarks ?? []).reduce(
    (acc, b) => {
      const project = b.project_name ?? "Unknown";
      if (!acc[project]) acc[project] = [];
      acc[project].push(b);
      return acc;
    },
    {} as Record<string, typeof bookmarks extends (infer T)[] | undefined ? T[] : never>,
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Bookmark className="size-6 text-primary" />
        <h1 className="text-2xl font-bold">Bookmarks</h1>
        {bookmarks && bookmarks.length > 0 && (
          <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600">
            {bookmarks.length}
          </span>
        )}
      </div>

      {isPending && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load bookmarks: {error.message}
        </div>
      )}

      {bookmarks && bookmarks.length === 0 && (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          <Bookmark className="mx-auto mb-2 size-8 opacity-50" />
          <p>No bookmarks yet.</p>
          <p className="text-xs mt-1">
            Click the bookmark icon on any message in a conversation to save it.
          </p>
        </div>
      )}

      {Object.entries(grouped).map(([project, items]) => (
        <section key={project}>
          <h2 className="text-sm font-medium text-muted-foreground mb-3">
            {project}
          </h2>
          <div className="space-y-2">
            {items.map((b) => (
              <div
                key={b.bookmark_id}
                className="group flex items-start gap-3 rounded-lg border bg-card p-3"
              >
                <Bookmark className="mt-0.5 size-4 shrink-0 text-amber-500" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/sessions/${b.session_id}#msg-${b.message_index}`}
                      className="font-medium text-sm hover:underline"
                    >
                      {b.name}
                    </Link>
                    <span className="text-xs text-muted-foreground">
                      msg #{b.message_index}
                    </span>
                  </div>
                  {b.description && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {b.description}
                    </p>
                  )}
                  {b.message_snippet && (
                    <p className="mt-1 text-xs text-muted-foreground/70 line-clamp-2 border-l-2 border-muted pl-2">
                      <span className={cn(
                        "font-medium",
                        b.message_role === "user" ? "text-blue-500" : "text-green-500",
                      )}>
                        {b.message_role === "user" ? "User" : "Assistant"}:
                      </span>{" "}
                      {b.message_snippet}
                    </p>
                  )}
                  <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                    <span>{new Date(b.created_at).toLocaleDateString()}</span>
                    <Link
                      to={`/sessions/${b.session_id}#msg-${b.message_index}`}
                      className="flex items-center gap-1 hover:text-foreground"
                    >
                      <MessageSquare className="size-3" />
                      View
                    </Link>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive"
                  onClick={() => deleteMutation.mutate(b.bookmark_id)}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

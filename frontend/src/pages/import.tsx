import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Database, FolderSync, Info, RefreshCw } from "lucide-react";

interface ImportEvent {
  type: string;
  project?: string;
  current?: number;
  total?: number;
  error?: string;
  projects?: number;
  sessions?: number;
  messages?: number;
  tool_uses?: number;
}

export default function ImportPage() {
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<ImportEvent[]>([]);

  const startImport = useCallback(() => {
    setRunning(true);
    setEvents([]);

    fetch("/api/import", { method: "POST" })
      .then(async (res) => {
        if (!res.ok) {
          setEvents((prev) => [
            ...prev,
            { type: "import_complete", error: `Import failed: ${res.status} ${res.statusText}` },
          ]);
          setRunning(false);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          setRunning(false);
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const event: ImportEvent = JSON.parse(line.slice(6));
                setEvents((prev) => [...prev, event]);
                if (event.type === "import_complete") {
                  setRunning(false);
                }
              } catch {
                // ignore
              }
            }
          }
        }
        setRunning(false);
      })
      .catch((err) => {
        setEvents((prev) => [
          ...prev,
          { type: "import_complete", error: `Network error: ${err.message}` },
        ]);
        setRunning(false);
      });
  }, []);

  const latest = events[events.length - 1];
  const complete = events.find((e) => e.type === "import_complete");
  const hasNewData =
    complete &&
    !complete.error &&
    ((complete.projects ?? 0) > 0 ||
      (complete.sessions ?? 0) > 0 ||
      (complete.messages ?? 0) > 0 ||
      (complete.tool_uses ?? 0) > 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Import</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Import conversation transcripts from <code className="rounded bg-muted px-1 py-0.5 text-xs">~/.claude/projects/</code> into the database.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border bg-card p-4 space-y-2">
          <div className="flex items-center gap-2">
            <FolderSync className="size-4 text-primary" />
            <h3 className="font-medium text-sm">Automatic file watcher</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            The API server automatically watches for new and updated session files.
            On startup it catches up on any changes that occurred while the server was stopped,
            then continues monitoring for new activity in real time. In most cases, your sessions
            are already up to date.
          </p>
        </div>

        <div className="rounded-lg border bg-card p-4 space-y-2">
          <div className="flex items-center gap-2">
            <RefreshCw className="size-4 text-primary" />
            <h3 className="font-medium text-sm">Manual import</h3>
          </div>
          <p className="text-sm text-muted-foreground">
            Performs a full scan of all project directories and re-checks every session file
            for new messages. Use this if you suspect the file watcher missed something, or
            after restoring data from a backup. Also rebuilds the full-text search index.
          </p>
        </div>
      </div>

      <Button onClick={startImport} disabled={running}>
        <Database className="size-4" />
        {running ? "Importing..." : "Run Full Import"}
      </Button>

      {running && latest?.type === "import_progress" && (
        <div className="space-y-2">
          <p className="text-sm">
            Processing project {latest.current}/{latest.total}:{" "}
            <span className="font-medium">{latest.project?.split("/").pop()}</span>
          </p>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-primary transition-all"
              style={{
                width: `${((latest.current ?? 0) / (latest.total ?? 1)) * 100}%`,
              }}
            />
          </div>
        </div>
      )}

      {complete && (
        <div className="rounded-lg border bg-card p-4 space-y-3">
          {complete.error ? (
            <>
              <h3 className="font-medium text-destructive">Import Failed</h3>
              <p className="text-sm text-destructive">{complete.error}</p>
            </>
          ) : hasNewData ? (
            <>
              <h3 className="font-medium">Import Complete</h3>
              <p className="text-sm text-muted-foreground">New data was imported:</p>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-md bg-muted/50 p-3 text-center">
                  <p className="text-2xl font-semibold tabular-nums">{complete.projects}</p>
                  <p className="text-xs text-muted-foreground">Projects</p>
                </div>
                <div className="rounded-md bg-muted/50 p-3 text-center">
                  <p className="text-2xl font-semibold tabular-nums">{complete.sessions}</p>
                  <p className="text-xs text-muted-foreground">Sessions</p>
                </div>
                <div className="rounded-md bg-muted/50 p-3 text-center">
                  <p className="text-2xl font-semibold tabular-nums">{complete.messages?.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">Messages</p>
                </div>
                <div className="rounded-md bg-muted/50 p-3 text-center">
                  <p className="text-2xl font-semibold tabular-nums">{complete.tool_uses?.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">Tool Uses</p>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-start gap-3">
                <Info className="size-5 text-muted-foreground mt-0.5 shrink-0" />
                <div>
                  <h3 className="font-medium">Already up to date</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    All {latest?.total ?? 0} projects were scanned and no new data was found.
                    The file watcher has already imported everything.
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

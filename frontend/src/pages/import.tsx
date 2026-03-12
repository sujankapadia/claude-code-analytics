import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";

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

    fetch("/api/import", { method: "POST" }).then(async (res) => {
      const reader = res.body?.getReader();
      if (!reader) return;

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
    });
  }, []);

  const latest = events[events.length - 1];
  const complete = events.find((e) => e.type === "import_complete");

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Import</h1>

      <p className="text-sm text-muted-foreground">
        Import conversation transcripts from ~/.claude/projects/ into the database.
      </p>

      <Button onClick={startImport} disabled={running}>
        {running ? "Importing..." : "Run Import"}
      </Button>

      {running && latest?.type === "import_progress" && (
        <div className="space-y-2">
          <p className="text-sm">
            Processing project {latest.current}/{latest.total}: {latest.project}
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
        <div className="rounded-lg border bg-card p-4">
          <h3 className="font-medium">Import Complete</h3>
          {complete.error ? (
            <p className="mt-1 text-sm text-destructive">{complete.error}</p>
          ) : (
            <ul className="mt-1 text-sm text-muted-foreground">
              <li>Projects: {complete.projects}</li>
              <li>Sessions: {complete.sessions}</li>
              <li>Messages: {complete.messages}</li>
              <li>Tool Uses: {complete.tool_uses}</li>
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

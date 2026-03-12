import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  fetchSessions,
  fetchProjects,
  fetchAnalysisTypes,
  runAnalysis,
  publishAnalysis,
} from "@/api/client";
import type { AnalysisResult } from "@/api/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export default function AnalysisPage() {
  const [projectId, setProjectId] = useState<string>("all");
  const [sessionId, setSessionId] = useState<string>("");
  const [analysisType, setAnalysisType] = useState<string>("decisions");
  const [customPrompt, setCustomPrompt] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [publishUrl, setPublishUrl] = useState<string | null>(null);

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  const { data: sessions } = useQuery({
    queryKey: ["sessions", { project_id: projectId === "all" ? undefined : projectId }],
    queryFn: () =>
      fetchSessions({
        project_id: projectId === "all" ? undefined : projectId,
      }),
  });

  const { data: analysisTypes } = useQuery({
    queryKey: ["analysis", "types"],
    queryFn: fetchAnalysisTypes,
  });

  const analysisMutation = useMutation({
    mutationFn: runAnalysis,
    onSuccess: (data) => {
      setResult(data);
      setPublishUrl(null);
    },
  });

  const publishMutation = useMutation({
    mutationFn: publishAnalysis,
    onSuccess: (data) => {
      setPublishUrl(data.url);
    },
  });

  const selectedSession = useMemo(
    () => sessions?.find((s) => s.session_id === sessionId),
    [sessions, sessionId],
  );

  const canRun = sessionId && analysisType && (analysisType !== "custom" || customPrompt.trim());

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analysis</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[400px_1fr]">
        {/* Left: Configuration */}
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4 space-y-4">
            <h2 className="text-sm font-medium">Configuration</h2>

            {/* Project filter */}
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">Project</label>
              <Select
                value={projectId}
                onValueChange={(v) => {
                  setProjectId(v);
                  setSessionId("");
                }}
              >
                <SelectTrigger className="h-8 text-xs">
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
            </div>

            {/* Session selector */}
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">Session</label>
              <Select value={sessionId} onValueChange={setSessionId}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Select a session" />
                </SelectTrigger>
                <SelectContent>
                  {sessions?.map((s) => (
                    <SelectItem key={s.session_id} value={s.session_id}>
                      <span className="font-mono">
                        {s.session_id.slice(0, 8)}
                      </span>
                      <span className="ml-2 text-muted-foreground">
                        {s.message_count} msgs ·{" "}
                        {s.project_name.split("/").pop()}
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Session info */}
            {selectedSession && (
              <div className="rounded border bg-muted/30 p-2 text-xs text-muted-foreground space-y-0.5">
                <p>
                  <span className="font-medium text-foreground">
                    {selectedSession.message_count}
                  </span>{" "}
                  messages ·{" "}
                  <span className="font-medium text-foreground">
                    {selectedSession.tool_use_count}
                  </span>{" "}
                  tool uses
                </p>
                <p>
                  {selectedSession.start_time
                    ? new Date(selectedSession.start_time).toLocaleString()
                    : "—"}
                </p>
              </div>
            )}

            {/* Analysis type */}
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">
                Analysis Type
              </label>
              <Select value={analysisType} onValueChange={setAnalysisType}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {analysisTypes &&
                    Object.entries(analysisTypes).map(([key, info]) => (
                      <SelectItem key={key} value={key}>
                        {info.name}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              {analysisTypes?.[analysisType] && (
                <p className="text-[10px] text-muted-foreground">
                  {analysisTypes[analysisType].description}
                </p>
              )}
            </div>

            {/* Custom prompt */}
            {analysisType === "custom" && (
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground">
                  Custom Prompt
                </label>
                <Textarea
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="Describe what you want to analyze..."
                  className="min-h-[100px] text-xs"
                />
              </div>
            )}

            {/* Run button */}
            <Button
              onClick={() =>
                analysisMutation.mutate({
                  session_id: sessionId,
                  analysis_type: analysisType,
                  custom_prompt:
                    analysisType === "custom" ? customPrompt : undefined,
                })
              }
              disabled={!canRun || analysisMutation.isPending}
              className="w-full"
            >
              {analysisMutation.isPending ? "Analyzing..." : "Run Analysis"}
            </Button>

            {analysisMutation.isError && (
              <p className="text-xs text-destructive">
                {analysisMutation.error.message}
              </p>
            )}
          </div>
        </div>

        {/* Right: Results */}
        <div className="min-h-[60vh]">
          {analysisMutation.isPending && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center space-y-2">
                <div className="mx-auto size-8 animate-spin rounded-full border-2 border-muted border-t-primary" />
                <p className="text-sm text-muted-foreground">
                  Running analysis...
                </p>
              </div>
            </div>
          )}

          {result && !analysisMutation.isPending && (
            <div className="space-y-4">
              {/* Result header */}
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  {result.model_name && (
                    <span className="mr-3 font-mono text-xs">
                      {result.model_name}
                    </span>
                  )}
                  {result.input_tokens != null && result.output_tokens != null && (
                    <span>
                      {formatNumber(result.input_tokens)} in /{" "}
                      {formatNumber(result.output_tokens)} out tokens
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(result.result_text);
                    }}
                  >
                    Copy
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      publishMutation.mutate({
                        analysis_content: result.result_text,
                        description: `Analysis: ${result.analysis_type} — ${result.session_id.slice(0, 8)}`,
                      })
                    }
                    disabled={publishMutation.isPending}
                  >
                    {publishMutation.isPending
                      ? "Publishing..."
                      : "Publish to Gist"}
                  </Button>
                </div>
              </div>

              {publishUrl && (
                <div className="rounded border bg-green-500/10 p-2 text-xs">
                  Published:{" "}
                  <a
                    href={publishUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline"
                  >
                    {publishUrl}
                  </a>
                </div>
              )}

              {publishMutation.isError && (
                <p className="text-xs text-destructive">
                  Publish failed: {publishMutation.error.message}
                </p>
              )}

              {/* Markdown-ish output */}
              <div
                className={cn(
                  "rounded-lg border bg-card p-5",
                  "prose prose-sm prose-invert max-w-none",
                  "prose-headings:font-semibold prose-headings:text-foreground",
                  "prose-p:text-foreground/90 prose-li:text-foreground/90",
                  "prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:text-xs",
                  "prose-pre:bg-muted prose-pre:p-3 prose-pre:text-xs",
                )}
              >
                <MarkdownContent text={result.result_text} />
              </div>
            </div>
          )}

          {!result && !analysisMutation.isPending && (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <p className="text-sm">
                Select a session and analysis type, then click "Run Analysis"
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Simple markdown-to-HTML renderer for analysis output. */
function MarkdownContent({ text }: { text: string }) {
  const html = useMemo(() => {
    let result = text
      // Escape HTML
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks
    result = result.replace(
      /```(\w*)\n([\s\S]*?)```/g,
      '<pre><code class="language-$1">$2</code></pre>',
    );

    // Inline code
    result = result.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Headers
    result = result.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
    result = result.replace(/^### (.+)$/gm, "<h3>$1</h3>");
    result = result.replace(/^## (.+)$/gm, "<h2>$1</h2>");
    result = result.replace(/^# (.+)$/gm, "<h1>$1</h1>");

    // Bold / italic
    result = result.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    result = result.replace(/\*(.+?)\*/g, "<em>$1</em>");

    // Unordered lists
    result = result.replace(/^- (.+)$/gm, "<li>$1</li>");
    result = result.replace(
      /(<li>[\s\S]*?<\/li>)/g,
      (match) => `<ul>${match}</ul>`,
    );
    // Collapse adjacent <ul> tags
    result = result.replace(/<\/ul>\s*<ul>/g, "");

    // Paragraphs (lines not already wrapped)
    result = result.replace(
      /^(?!<[huplo])([\s\S]+?)(?=\n\n|\n<[huplo]|$)/gm,
      (match) => {
        if (match.trim() === "") return match;
        if (match.startsWith("<")) return match;
        return `<p>${match.trim()}</p>`;
      },
    );

    return result;
  }, [text]);

  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

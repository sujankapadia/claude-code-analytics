import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  fetchSessions,
  fetchProjects,
  fetchAnalysisTypes,
  fetchProviderInfo,
  fetchProviderModels,
  runAnalysis,
  publishAnalysis,
} from "@/api/client";
import type { AnalysisResult, ProviderConfig, ProviderInfo } from "@/api/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Combobox,
  ComboboxInput,
  ComboboxContent,
  ComboboxList,
  ComboboxItem,
  ComboboxEmpty,
} from "@/components/ui/combobox";
import { cn } from "@/lib/utils";
import { ChevronDownIcon, ChevronRightIcon } from "lucide-react";

type ScopeMode = "entire" | "time_range" | "search_hit";

const STORAGE_KEY = "claude-analytics:provider-config";

function loadProviderConfig(): ProviderConfig | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ProviderConfig) : null;
  } catch {
    return null;
  }
}

function saveProviderConfig(config: ProviderConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

function defaultConfigFromInfo(info: ProviderInfo): ProviderConfig {
  // Match server provider to a preset
  const matchedPreset = info.presets.find((p) => p.base_url === info.base_url);
  return {
    preset: matchedPreset?.name ?? "Custom",
    base_url: info.base_url ?? "",
    api_key: "",
    model: info.default_model ?? "",
  };
}

export default function AnalysisPage() {
  const [searchParams] = useSearchParams();
  const [projectId, setProjectId] = useState<string>("all");
  const [sessionSearch, setSessionSearch] = useState("");
  const [sessionId, setSessionId] = useState<string>(() => searchParams.get("session_id") ?? "");
  const [analysisType, setAnalysisType] = useState<string>("decisions");
  const [customPrompt, setCustomPrompt] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [publishUrl, setPublishUrl] = useState<string | null>(null);
  const [modelSettingsOpen, setModelSettingsOpen] = useState(false);
  const [providerConfig, setProviderConfig] = useState<ProviderConfig>(
    () => loadProviderConfig() ?? { preset: "", base_url: "", api_key: "", model: "" },
  );
  const [configInitialized, setConfigInitialized] = useState(false);

  // Scope state
  const [scopeMode, setScopeMode] = useState<ScopeMode>(() =>
    searchParams.get("message_index") ? "search_hit" : "entire",
  );
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [messageIndex] = useState<number | null>(() => {
    const idx = searchParams.get("message_index");
    return idx ? parseInt(idx, 10) : null;
  });
  const [contextWindow, setContextWindow] = useState(20);

  const { data: providerInfo } = useQuery({
    queryKey: ["analysis", "provider-info"],
    queryFn: fetchProviderInfo,
  });

  // Initialize config from server defaults when no localStorage config exists
  useEffect(() => {
    if (configInitialized || !providerInfo) return;
    const saved = loadProviderConfig();
    if (saved) {
      setProviderConfig(saved);
    } else {
      const defaults = defaultConfigFromInfo(providerInfo);
      setProviderConfig(defaults);
      saveProviderConfig(defaults);
    }
    setConfigInitialized(true);
  }, [providerInfo, configInitialized]);

  const updateConfig = useCallback(
    (patch: Partial<ProviderConfig>) => {
      setProviderConfig((prev) => {
        const next = { ...prev, ...patch };
        saveProviderConfig(next);
        return next;
      });
    },
    [],
  );

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

  const filteredSessions = useMemo(() => {
    if (!sessions) return [];
    const q = sessionSearch.toLowerCase().trim();
    if (!q) return sessions;
    return sessions.filter((s) => {
      return (
        (s.first_user_message?.toLowerCase().includes(q) ?? false) ||
        s.project_name.toLowerCase().includes(q) ||
        s.session_id.toLowerCase().includes(q)
      );
    });
  }, [sessions, sessionSearch]);

  const selectedSession = useMemo(
    () => sessions?.find((s) => s.session_id === sessionId),
    [sessions, sessionId],
  );

  // Default time range inputs when session changes
  useEffect(() => {
    if (selectedSession) {
      if (selectedSession.start_time) {
        setStartTime(toDatetimeLocal(selectedSession.start_time));
      }
      if (selectedSession.end_time) {
        setEndTime(toDatetimeLocal(selectedSession.end_time));
      }
    }
  }, [selectedSession]);

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
                  setProjectId(v ?? "");
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
            <SessionPicker
              sessions={filteredSessions}
              selectedSession={selectedSession ?? null}
              searchValue={sessionSearch}
              onSearchChange={setSessionSearch}
              onSelect={(id) => {
                setSessionId(id);
                setSessionSearch("");
              }}
            />

            {/* Analysis type */}
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">
                Analysis Type
              </label>
              <Select value={analysisType} onValueChange={(v) => setAnalysisType(v ?? "")}>
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

            {/* Scope */}
            <div className="space-y-2">
              <label className="text-xs text-muted-foreground">Scope</label>
              <div className="flex gap-1">
                {([
                  ["entire", "Entire Session"],
                  ["time_range", "Time Range"],
                  ["search_hit", "Around Search Hit"],
                ] as const).map(([mode, label]) => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setScopeMode(mode)}
                    className={cn(
                      "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
                      scopeMode === mode
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {scopeMode === "time_range" && (
                <div className="space-y-2 rounded-md border bg-muted/30 p-3">
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground">Start</label>
                    <Input
                      type="datetime-local"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      className="h-7 text-xs"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground">End</label>
                    <Input
                      type="datetime-local"
                      value={endTime}
                      onChange={(e) => setEndTime(e.target.value)}
                      className="h-7 text-xs"
                    />
                  </div>
                </div>
              )}

              {scopeMode === "search_hit" && (
                <div className="space-y-2 rounded-md border bg-muted/30 p-3">
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground">Message Index</label>
                    <p className="text-xs font-mono">
                      {messageIndex != null ? `#${messageIndex}` : "Navigate from Search to set"}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground">
                      Context Window: {contextWindow} messages
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={50}
                      value={contextWindow}
                      onChange={(e) => setContextWindow(parseInt(e.target.value, 10))}
                      className="w-full accent-primary"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Model Settings (collapsible) */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => setModelSettingsOpen(!modelSettingsOpen)}
                className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
              >
                {modelSettingsOpen ? (
                  <ChevronDownIcon className="size-3" />
                ) : (
                  <ChevronRightIcon className="size-3" />
                )}
                Model Settings
              </button>

              {modelSettingsOpen && (
                <div className="space-y-3 rounded-md border bg-muted/30 p-3">
                  {/* Provider preset */}
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground">
                      Provider
                    </label>
                    <Select
                      value={providerConfig.preset}
                      onValueChange={(v) => {
                        if (!v) return;
                        const preset = providerInfo?.presets.find(
                          (p) => p.name === v,
                        );
                        updateConfig({
                          preset: v,
                          base_url: preset?.base_url ?? "",
                          model: preset?.default_model ?? providerConfig.model,
                        });
                      }}
                    >
                      <SelectTrigger className="h-7 text-xs">
                        <SelectValue placeholder="Select provider..." />
                      </SelectTrigger>
                      <SelectContent>
                        {providerInfo?.presets.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Base URL (shown for Custom preset) */}
                  {providerConfig.preset === "Custom" && (
                    <div className="space-y-1">
                      <label className="text-[10px] text-muted-foreground">
                        Base URL
                      </label>
                      <Input
                        value={providerConfig.base_url}
                        onChange={(e) =>
                          updateConfig({ base_url: e.target.value })
                        }
                        placeholder="http://localhost:8080/v1"
                        className="h-7 text-xs"
                      />
                    </div>
                  )}

                  {/* API Key */}
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground">
                      API Key (optional)
                    </label>
                    <Input
                      type="password"
                      value={providerConfig.api_key}
                      onChange={(e) =>
                        updateConfig({ api_key: e.target.value })
                      }
                      placeholder="sk-..."
                      className="h-7 text-xs"
                    />
                  </div>

                  {/* Model selector */}
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground">
                      Model
                    </label>
                    <ModelCombobox
                      value={providerConfig.model}
                      onChange={(v) => updateConfig({ model: v })}
                      quickModels={providerInfo?.quick_select_models ?? []}
                      showQuickModels={providerConfig.base_url.includes("openrouter.ai")}
                      baseUrl={providerConfig.base_url}
                      apiKey={providerConfig.api_key}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Run button */}
            <Button
              onClick={() =>
                analysisMutation.mutate({
                  session_id: sessionId,
                  analysis_type: analysisType,
                  custom_prompt:
                    analysisType === "custom" ? customPrompt : undefined,
                  model: providerConfig.model || undefined,
                  base_url: providerConfig.base_url || undefined,
                  api_key: providerConfig.api_key || undefined,
                  start_time: scopeMode === "time_range" && startTime ? new Date(startTime).toISOString() : undefined,
                  end_time: scopeMode === "time_range" && endTime ? new Date(endTime).toISOString() : undefined,
                  message_index: scopeMode === "search_hit" && messageIndex != null ? messageIndex : undefined,
                  context_window: scopeMode === "search_hit" ? contextWindow : undefined,
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

function ModelCombobox({
  value,
  onChange,
  quickModels,
  showQuickModels,
  baseUrl,
  apiKey,
}: {
  value: string;
  onChange: (v: string) => void;
  quickModels: { label: string; value: string }[];
  showQuickModels: boolean;
  baseUrl: string;
  apiKey: string;
}) {
  const isOpenRouter = baseUrl.includes("openrouter.ai");
  const canFetchModels = !!baseUrl && !isOpenRouter;

  const { data: remoteModels, isLoading: modelsLoading } = useQuery({
    queryKey: ["analysis", "models", baseUrl, apiKey],
    queryFn: () => fetchProviderModels({ base_url: baseUrl, api_key: apiKey || undefined }),
    enabled: canFetchModels,
    staleTime: 60_000,
    retry: false,
  });

  const items = useMemo(() => {
    if (showQuickModels) {
      return quickModels.map((m) => ({ label: m.label, value: m.value }));
    }
    if (remoteModels) {
      return remoteModels.map((m) => ({ label: m.id, value: m.id }));
    }
    return [];
  }, [quickModels, showQuickModels, remoteModels]);

  const placeholder = modelsLoading
    ? "Loading models..."
    : items.length > 0
      ? "Select or type a model..."
      : "Type a model name...";

  return (
    <Combobox
      value={value}
      onValueChange={(val) => onChange(val as string)}
    >
      <ComboboxInput
        placeholder={placeholder}
        className="h-7 text-xs"
        showClear={!!value}
      />
      <ComboboxContent>
        <ComboboxList>
          <ComboboxEmpty>
            {modelsLoading ? "Loading..." : "Type a model ID..."}
          </ComboboxEmpty>
          {items.map((item) => (
            <ComboboxItem key={item.value} value={item.value}>
              <span className="text-xs">{item.label}</span>
            </ComboboxItem>
          ))}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
}

function SessionPicker({
  sessions,
  selectedSession,
  searchValue,
  onSearchChange,
  onSelect,
}: {
  sessions: import("@/api/types").SessionSummary[];
  selectedSession: import("@/api/types").SessionSummary | null;
  searchValue: string;
  onSearchChange: (v: string) => void;
  onSelect: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  return (
    <div className="space-y-1.5">
      <label className="text-xs text-muted-foreground">Session</label>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex h-8 w-full items-center rounded-md border bg-transparent px-3 text-left text-xs",
          "hover:bg-muted/50 focus:outline-none focus:ring-1 focus:ring-ring",
          !selectedSession && "text-muted-foreground",
        )}
      >
        <span className="min-w-0 flex-1 truncate">
          {selectedSession
            ? selectedSession.first_user_message?.slice(0, 60) ??
              selectedSession.session_id.slice(0, 8)
            : "Select a session..."}
        </span>
        <svg
          className="ml-2 size-3 shrink-0 text-muted-foreground"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="rounded-lg border bg-popover shadow-md">
          <div className="border-b p-2">
            <input
              ref={inputRef}
              type="text"
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search by message, project..."
              className="w-full bg-transparent text-xs outline-none placeholder:text-muted-foreground"
            />
          </div>
          <div className="max-h-64 overflow-auto p-1">
            {sessions.length === 0 ? (
              <p className="py-4 text-center text-xs text-muted-foreground">
                No matching sessions
              </p>
            ) : (
              sessions.map((s) => (
                <button
                  key={s.session_id}
                  type="button"
                  onClick={() => {
                    onSelect(s.session_id);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full cursor-default items-center rounded-md px-2 py-1.5 text-left",
                    s.session_id === selectedSession?.session_id
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted/50",
                  )}
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs">
                      {s.first_user_message
                        ? s.first_user_message.slice(0, 80) +
                          (s.first_user_message.length > 80 ? "..." : "")
                        : s.session_id.slice(0, 8)}
                    </div>
                    <div className="truncate text-[10px] text-muted-foreground">
                      {s.project_name.split("/").pop()} ·{" "}
                      {s.start_time
                        ? new Date(s.start_time).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                          })
                        : "—"}{" "}
                      · {s.message_count} msgs · {s.tool_use_count} tools
                      {s.duration_seconds != null && (
                        <> · {formatDuration(s.duration_seconds)}</>
                      )}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
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

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

/** Convert an ISO timestamp to a value suitable for datetime-local inputs. */
function toDatetimeLocal(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

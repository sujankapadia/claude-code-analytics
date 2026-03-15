import { useState, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Search, Copy, Check, Loader2 } from "lucide-react";
import { findExamplePrompts, findExampleSessions, fetchProjects } from "@/api/client";
import type { FindPromptsResponse, FindSessionsResponse } from "@/api/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Mode = "prompts" | "sessions";

export default function ExamplesPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("prompts");
  const [projectId, setProjectId] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  const promptsMutation = useMutation({
    mutationFn: findExamplePrompts,
  });

  const sessionsMutation = useMutation({
    mutationFn: findExampleSessions,
  });

  const isPending = promptsMutation.isPending || sessionsMutation.isPending;
  const error = promptsMutation.error || sessionsMutation.error;

  const handleSearch = () => {
    if (!query.trim() || isPending) return;
    if (mode === "prompts") {
      promptsMutation.mutate({
        query,
        project_id: projectId || undefined,
        max_results: 5,
      });
      sessionsMutation.reset();
    } else {
      sessionsMutation.mutate({
        query,
        project_id: projectId || undefined,
        max_results: 5,
      });
      promptsMutation.reset();
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Find Examples</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Search your conversation history for prompts and workflows using natural language.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex max-w-2xl items-center gap-3">
        <div className="inline-flex rounded-lg border bg-muted p-1">
          <button
            onClick={() => setMode("prompts")}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              mode === "prompts"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Prompts
          </button>
          <button
            onClick={() => setMode("sessions")}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              mode === "sessions"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Sessions
          </button>
        </div>
        <span className="text-xs text-muted-foreground">
          {mode === "prompts"
            ? "Find specific user prompts you can share as templates"
            : "Find sessions where a technique or workflow was used"}
        </span>
      </div>

      {/* Search input */}
      <div className="flex max-w-2xl gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            ref={inputRef}
            placeholder={
              mode === "prompts"
                ? 'e.g. "How do I use Playwright to test a component?"'
                : 'e.g. "sessions where I debugged a database issue"'
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSearch();
            }}
            className="pl-9"
          />
        </div>
        <Button onClick={handleSearch} disabled={!query.trim() || isPending}>
          {isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            "Search"
          )}
        </Button>
      </div>

      {/* Project filter */}
      <div className="max-w-2xl">
        <select
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          className="rounded border bg-background px-2 py-1.5 text-sm"
        >
          <option value="">All projects</option>
          {projects?.map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.project_name.split("/").pop()}
            </option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <p className="text-sm text-destructive">{(error as Error).message}</p>
      )}

      {/* Loading */}
      {isPending && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Searching with FTS, then ranking with LLM...
        </div>
      )}

      {/* Prompt results */}
      {promptsMutation.data && (
        <PromptResults data={promptsMutation.data} />
      )}

      {/* Session results */}
      {sessionsMutation.data && (
        <SessionResults data={sessionsMutation.data} />
      )}
    </div>
  );
}

function PromptResults({ data }: { data: FindPromptsResponse }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span>
          {data.prompts.length} result{data.prompts.length !== 1 ? "s" : ""} from{" "}
          {data.candidate_count} candidates
        </span>
        {data.input_tokens != null && (
          <span className="text-xs">
            ({data.input_tokens.toLocaleString()} input tokens · {data.model_name})
          </span>
        )}
      </div>

      {data.prompts.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No matching prompts found. Try different keywords.
        </p>
      )}

      {data.prompts.map((prompt, i) => (
        <PromptCard
          key={`${prompt.session_id}-${prompt.message_index}`}
          prompt={prompt}
          index={i}
        />
      ))}
    </div>
  );
}

function PromptCard({
  prompt,
  index,
}: {
  prompt: FindPromptsResponse["prompts"][number];
  index: number;
}) {
  const [copied, setCopied] = useState(false);
  const projectShort = prompt.project_name.split("/").pop();

  const handleCopy = async () => {
    await navigator.clipboard.writeText(prompt.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border">
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-2">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-medium">#{index + 1}</span>
          <span className="text-muted-foreground">·</span>
          <Link
            to={`/sessions/${prompt.session_id}#msg-${prompt.message_index}`}
            className="font-mono text-xs hover:underline"
          >
            {prompt.session_id.slice(0, 12)}
          </Link>
          <span className="text-muted-foreground">·</span>
          <span className="text-xs text-muted-foreground">{projectShort}</span>
          {prompt.timestamp && (
            <>
              <span className="text-muted-foreground">·</span>
              <span className="text-xs text-muted-foreground">
                {new Date(prompt.timestamp).toLocaleDateString()}
              </span>
            </>
          )}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
          title="Copy prompt to clipboard"
        >
          {copied ? (
            <>
              <Check className="size-3.5" />
              Copied
            </>
          ) : (
            <>
              <Copy className="size-3.5" />
              Copy
            </>
          )}
        </button>
      </div>
      <div className="px-4 py-3">
        <p className="text-xs text-primary mb-2">{prompt.relevance}</p>
        <pre className="whitespace-pre-wrap text-sm leading-relaxed">
          {prompt.content}
        </pre>
      </div>
    </div>
  );
}

function SessionResults({ data }: { data: FindSessionsResponse }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span>
          {data.matches.length} result{data.matches.length !== 1 ? "s" : ""} from{" "}
          {data.candidate_count} candidates
        </span>
        {data.input_tokens != null && (
          <span className="text-xs">
            ({data.input_tokens.toLocaleString()} input tokens · {data.model_name})
          </span>
        )}
      </div>

      {data.matches.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No matching sessions found. Try different keywords.
        </p>
      )}

      {data.matches.map((match) => (
        <div key={match.session_id} className="rounded-lg border">
          <div className="border-b bg-muted/30 px-4 py-2">
            <div className="flex items-center gap-2">
              <Link
                to={`/sessions/${match.session_id}`}
                className="font-mono text-sm font-medium hover:underline"
              >
                {match.session_id.slice(0, 12)}
              </Link>
              <span className="text-xs text-muted-foreground">
                {match.project_name.split("/").pop()} · {match.message_count} msgs ·{" "}
                {match.tool_use_count} tools
              </span>
            </div>
            {match.first_user_message && (
              <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
                {match.first_user_message}
              </p>
            )}
          </div>
          <div className="px-4 py-3 space-y-2">
            <p className="text-sm text-primary">{match.relevance}</p>
            {match.suggested_excerpt_range && (
              <p className="text-xs text-muted-foreground">
                Suggested range: {match.suggested_excerpt_range}
              </p>
            )}
            {match.matching_excerpts.length > 0 && (
              <div className="space-y-1.5 mt-2">
                <span className="text-xs font-medium text-muted-foreground">
                  Matching excerpts:
                </span>
                {match.matching_excerpts.map((exc, i) => (
                  <Link
                    key={i}
                    to={`/sessions/${match.session_id}#msg-${exc.message_index}`}
                    className="block rounded bg-muted/50 px-3 py-2 text-xs hover:bg-muted"
                  >
                    <span className="font-medium">
                      [{exc.role}] msg {exc.message_index}
                    </span>
                    <p className="mt-0.5 text-muted-foreground line-clamp-2">
                      {exc.content}
                    </p>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

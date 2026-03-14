import { useState, useMemo } from "react";
import { ChevronRight, AlertTriangle } from "lucide-react";
import type { ToolUse } from "@/api/types";
import { cn } from "@/lib/utils";

/** Max characters to show in collapsed tool result. */
const RESULT_PREVIEW_LEN = 300;

/** Parse JSON tool_input safely. */
function parseInput(raw: string | null): Record<string, unknown> | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/** Render a diff-style view for Edit tool inputs. */
function EditDiff({ input }: { input: Record<string, unknown> }) {
  const filePath = input.file_path as string | undefined;
  const oldStr = input.old_string as string | undefined;
  const newStr = input.new_string as string | undefined;

  return (
    <div className="space-y-1">
      {filePath && (
        <p className="text-xs text-muted-foreground font-mono">{filePath}</p>
      )}
      {oldStr && (
        <pre className="rounded bg-red-500/10 px-2 py-1 text-xs font-mono whitespace-pre-wrap text-red-400">
          {oldStr.split("\n").map((line, i) => (
            <span key={i}>
              {"- "}{line}{"\n"}
            </span>
          ))}
        </pre>
      )}
      {newStr && (
        <pre className="rounded bg-green-500/10 px-2 py-1 text-xs font-mono whitespace-pre-wrap text-green-400">
          {newStr.split("\n").map((line, i) => (
            <span key={i}>
              {"+ "}{line}{"\n"}
            </span>
          ))}
        </pre>
      )}
    </div>
  );
}

/** Render Bash command with description. */
function BashCommand({ input }: { input: Record<string, unknown> }) {
  const command = input.command as string | undefined;
  const description = input.description as string | undefined;

  return (
    <div className="space-y-1">
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      {command && (
        <pre className="rounded bg-muted px-2 py-1 text-xs font-mono whitespace-pre-wrap">
          $ {command}
        </pre>
      )}
    </div>
  );
}

/** Render Read/Write file path. */
function FilePath({ input }: { input: Record<string, unknown> }) {
  const filePath = input.file_path as string | undefined;
  const content = input.content as string | undefined;

  return (
    <div className="space-y-1">
      {filePath && (
        <p className="text-xs font-mono text-muted-foreground">{filePath}</p>
      )}
      {content && (
        <pre className="max-h-40 overflow-auto rounded bg-muted px-2 py-1 text-xs font-mono whitespace-pre-wrap">
          {content.length > 500 ? content.slice(0, 500) + "\n..." : content}
        </pre>
      )}
    </div>
  );
}

/** Render tool input based on tool type. */
function ToolInput({ toolName, input }: { toolName: string; input: Record<string, unknown> }) {
  if (toolName === "Edit") return <EditDiff input={input} />;
  if (toolName === "Bash") return <BashCommand input={input} />;
  if (toolName === "Read" || toolName === "Write") return <FilePath input={input} />;
  if (toolName === "Grep" || toolName === "Glob") {
    const pattern = (input.pattern ?? input.glob) as string | undefined;
    const path = input.path as string | undefined;
    return (
      <div className="space-y-1">
        {pattern && (
          <pre className="rounded bg-muted px-2 py-1 text-xs font-mono">{pattern}</pre>
        )}
        {path && (
          <p className="text-xs text-muted-foreground font-mono">{path}</p>
        )}
      </div>
    );
  }

  // Generic: show JSON
  return (
    <pre className="max-h-40 overflow-auto rounded bg-muted px-2 py-1 text-xs font-mono whitespace-pre-wrap">
      {JSON.stringify(input, null, 2)}
    </pre>
  );
}

export function ToolCallCard({ tool }: { tool: ToolUse }) {
  const [expanded, setExpanded] = useState(false);
  const parsed = useMemo(() => parseInput(tool.tool_input), [tool.tool_input]);

  const resultPreview = useMemo(() => {
    if (!tool.tool_result) return null;
    if (tool.tool_result.length <= RESULT_PREVIEW_LEN) return tool.tool_result;
    return tool.tool_result.slice(0, RESULT_PREVIEW_LEN) + "…";
  }, [tool.tool_result]);

  return (
    <div
      className={cn(
        "rounded border text-sm",
        tool.is_error ? "border-red-500/30 bg-red-500/5" : "border-border bg-card"
      )}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-muted/50 transition-colors"
      >
        <ChevronRight
          className={cn(
            "size-3.5 shrink-0 transition-transform",
            expanded && "rotate-90"
          )}
        />
        <span className="font-mono text-xs font-medium">{tool.tool_name}</span>
        {tool.is_error && (
          <AlertTriangle className="size-3.5 text-red-500" />
        )}
        {parsed && tool.tool_name === "Bash" && typeof parsed.description === "string" && (
          <span className="truncate text-xs text-muted-foreground">
            {parsed.description}
          </span>
        )}
        {parsed && (tool.tool_name === "Read" || tool.tool_name === "Write" || tool.tool_name === "Edit") && typeof parsed.file_path === "string" && (
          <span className="truncate text-xs text-muted-foreground font-mono">
            {parsed.file_path.split("/").slice(-2).join("/")}
          </span>
        )}
      </button>

      {expanded && (
        <div className="space-y-2 border-t px-3 py-2">
          {parsed && <ToolInput toolName={tool.tool_name} input={parsed} />}
          {tool.tool_result && (
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                {tool.is_error ? "Error" : "Result"}
              </p>
              <pre
                className={cn(
                  "max-h-60 overflow-auto rounded px-2 py-1 text-xs font-mono whitespace-pre-wrap",
                  tool.is_error ? "bg-red-500/10 text-red-400" : "bg-muted"
                )}
              >
                {expanded ? tool.tool_result : resultPreview}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

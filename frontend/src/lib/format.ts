/** Resolve CSS custom property to a computed color string usable in SVG attributes. */
export function getCssColor(varName: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(varName)
    .trim();
}

/** Return resolved chart palette colors (chart-1 through chart-5). */
export function getChartColors(): string[] {
  return [1, 2, 3, 4, 5].map((i) => getCssColor(`--chart-${i}`));
}

/** Extract the last path segment from a project name/path. */
export function shortProjectName(name: string): string {
  return name.split("/").filter(Boolean).pop() ?? name;
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return n.toString();
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

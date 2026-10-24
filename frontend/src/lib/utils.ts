export { cn } from "cn"

/** The query string a link to another tab carries: only the run and plan, never a screen's own ?module=, ?unit= or ?path=. */
export function scopedSearch(params: URLSearchParams): string {
  const kept = new URLSearchParams([...params].filter(([key]) => key === 'plan' || key === 'run'))
  return kept.size ? `?${kept}` : ''
}

const FILLER = new Set(['the', 'and', 'for', 'are', 'how', 'what', 'where', 'when', 'why', 'does', 'that', 'this', 'with', 'from']);

/** The query words worth marking in a snippet: three letters or more, and not filler. */
export function queryWords(query: string): string[] {
  return [...new Set(query.toLowerCase().match(/\w{3,}/g) ?? [])].filter((w) => !FILLER.has(w));
}

/** Up to `n` lines of a hit, starting one line above the first that has a query word. */
export function excerpt(snippet: string, words: string[], n = 4): string {
  const lines = snippet.split('\n');
  const start = Math.max(0, lines.findIndex((l) => words.some((w) => l.toLowerCase().includes(w))) - 1);
  return lines.slice(start, start + n).join('\n');
}

/** The text cut at each query word, case-insensitively: the odd parts are the matches. */
export function splitAtWords(text: string, words: string[]): string[] {
  // \w words carry no regex syntax, so they need no escaping. Longest first, so "rounded" beats "round".
  const alternatives = [...words].sort((a, b) => b.length - a.length).join('|');
  return words.length ? text.split(new RegExp(`(${alternatives})`, 'gi')) : [text];
}

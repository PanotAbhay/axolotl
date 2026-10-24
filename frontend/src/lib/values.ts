import type { CaseOutcome } from '@/types/contracts';

/** A SHARED_CONTRACTS §5 value as Python would write it: Decimal reads as its digits, a tuple as (a, b). */
export function py(v: unknown): string {
  if (v === null || v === undefined) return 'None';
  if (typeof v === 'boolean') return v ? 'True' : 'False';
  if (typeof v === 'string') return JSON.stringify(v);
  if (typeof v !== 'object') return String(v);
  if (Array.isArray(v)) return `[${v.map(py).join(', ')}]`;
  const o = v as Record<string, unknown>;
  const items = (xs: unknown) => (Array.isArray(xs) ? xs : []);
  if ('__decimal__' in o) return String(o.__decimal__);
  if ('__float__' in o) return String(o.__float__);
  if ('__datetime__' in o) return String(o.__datetime__);
  if ('__date__' in o) return String(o.__date__);
  if ('__tuple__' in o) {
    const t = items(o.__tuple__).map(py);
    return `(${t.join(', ')}${t.length === 1 ? ',' : ''})`;
  }
  if ('__set__' in o) return `{${items(o.__set__).map(py).join(', ')}}`;
  if ('__dict_items__' in o) return `{${items(o.__dict_items__).map((kv) => `${py(items(kv)[0])}: ${py(items(kv)[1])}`).join(', ')}}`;
  if ('__object__' in o) {
    const fields = Object.entries((o.fields ?? {}) as Record<string, unknown>);
    return `${String(o.__object__)}(${fields.map(([k, x]) => `${k}=${py(x)}`).join(', ')})`;
  }
  return `{${Object.entries(o).map(([k, x]) => `${JSON.stringify(k)}: ${py(x)}`).join(', ')}}`;
}

/** What a call returned, or how it ended. Exceptions match on type only, so the message is context. */
export function outcome(o: CaseOutcome): string {
  if (o.status === 'raised') return `raises ${o.exception_type ?? 'an exception'}${o.exception_message ? `: ${o.exception_message}` : ''}`;
  if (o.status === 'timeout') return 'timed out';
  if (o.status === 'harness_error') return 'harness error';
  return py(o.value);
}

export const call = (fn: string, args: unknown[], kwargs: Record<string, unknown>) =>
  `${fn}(${[...args.map(py), ...Object.entries(kwargs).map(([k, v]) => `${k}=${py(v)}`)].join(', ')})`;

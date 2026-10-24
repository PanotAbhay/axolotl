import { HourglassIcon, InfoIcon, MagnifyingGlassIcon, XCircleIcon } from '@phosphor-icons/react';
import { useQuery } from '@tanstack/react-query';
import { cn } from 'cn';
import { useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';

import { ApiError, getGraph, searchRepository } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { excerpt, queryWords, splitAtWords } from '@/lib/search';
import { GraphArea } from '@/screens/GraphScreen';
import type { SearchHit, SearchMode } from '@/types/contracts';

const MODES: [SearchMode, string][] = [
  ['keyword', 'Keyword'],
  ['vector', 'Vector'],
  ['hybrid', 'Hybrid'],
];
const NOT_READY_POLL_MS = 3000;

type NotReady = { state?: string; index?: string; embedded?: number; total?: number | null; reason?: string | null };

// An index on its way: ask again until it lands. The backend checks before it embeds the query, so asking spends no quota.
const building = (e: unknown) =>
  e instanceof ApiError && e.code === 'SEARCH_INDEX_NOT_READY' && ['indexing', 'building'].includes(String(e.details.state));

function ranks(hit: SearchHit) {
  const rank = (n: number | null) => (n ? `#${n}` : 'no match');
  if (hit.match_method === 'keyword') return `Keyword ${rank(hit.keyword_rank)}`;
  if (hit.match_method === 'vector') return `Vector ${rank(hit.vector_rank)}`;
  // Native $rankFusion's breakdown is best effort; without it, only the fused rank is known.
  if (!hit.keyword_rank && !hit.vector_rank) return `Hybrid #${hit.rank}`;
  return `Hybrid, keyword ${rank(hit.keyword_rank)}, vector ${rank(hit.vector_rank)}`;
}

/** 503 SEARCH_INDEX_NOT_READY is an index on its way or gone, never "no results" (#20). */
function NotReadyNotice({ error, onKeyword }: { error: ApiError; onKeyword?: () => void }) {
  const d = error.details as NotReady;
  const waiting = building(error);
  return (
    <div className="m-4 flex items-start gap-2 rounded-md border bg-card px-4 py-3">
      {waiting ? (
        <HourglassIcon size={20} aria-hidden className="flex-none" />
      ) : (
        <XCircleIcon size={20} aria-hidden className="flex-none text-failed" />
      )}
      <div className="flex flex-col items-start gap-2 text-sm">
        {d.state === 'indexing' ? (
          <span>
            Index building{d.total ? `: ${d.embedded ?? 0} of ${d.total} chunks embedded` : ''}. Keyword search works now;
            these results appear when it finishes.
          </span>
        ) : d.state === 'building' ? (
          <span>The {d.index} index is still building in Atlas. These results appear when it’s ready.</span>
        ) : d.state === 'failed' ? (
          <span className="flex flex-col">
            Search indexing stopped, so vector and hybrid search are unavailable here. Keyword search still works.
            {d.reason && <span className="break-words text-muted-foreground">{d.reason}</span>}
          </span>
        ) : (
          <span>{error.message}</span>
        )}
        {onKeyword && (
          <Button variant="outline" onClick={onKeyword}>
            Search by keyword
          </Button>
        )}
      </div>
    </div>
  );
}

function Hit({ hit, words, picked, onPick }: { hit: SearchHit; words: string[]; picked: boolean; onPick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={picked}
      onClick={onPick}
      className={cn(
        'flex w-full flex-col gap-2 border-b px-4 py-3 text-left transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring',
        picked && 'rounded-md outline-2 -outline-offset-2 outline-foreground',
      )}
    >
      <span className="flex items-baseline gap-2 text-sm">
        <span className="truncate font-mono font-medium">{hit.path}</span>
        <span className="whitespace-nowrap text-muted-foreground">
          lines {hit.start_line}–{hit.end_line}
        </span>
        <span className="ml-auto whitespace-nowrap text-muted-foreground">{ranks(hit)}</span>
      </span>
      {hit.qualified_name && <span className="truncate font-mono text-sm text-muted-foreground">{hit.qualified_name}</span>}
      <span className="block overflow-hidden rounded-sm border bg-code px-3 py-2 font-mono text-sm leading-5 whitespace-pre">
        {splitAtWords(excerpt(hit.snippet, words), words).map((part, i) =>
          i % 2 ? (
            <mark key={i} className="rounded-[2px] bg-neutral-tint font-semibold text-foreground">
              {part}
            </mark>
          ) : (
            part
          ),
        )}
      </span>
    </button>
  );
}

/** 09 Search: code chunks by keyword, meaning or both, each leading to its module on the graph. Template: kit.js s09. */
export default function SearchScreen() {
  const { repoId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const module = params.get('module');
  const runId = params.get('run');
  const [draft, setDraft] = useState('');
  // Searches run on Enter, not per keystroke: each vector or hybrid search embeds the query once.
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<SearchMode>('hybrid');
  const [picked, setPicked] = useState<string | null>(null);
  const graph = useQuery({ queryKey: ['graph', repoId, runId], queryFn: () => getGraph(repoId, runId) });
  const results = useQuery({
    queryKey: ['search', repoId, query, mode],
    queryFn: () => searchRepository(repoId, query, mode),
    enabled: Boolean(query),
    refetchInterval: (q) => (building(q.state.error) ? NOT_READY_POLL_MS : false),
  });
  const words = queryWords(query);

  const select = (id: string | null) =>
    setParams(
      (p) => {
        if (id) p.set('module', id);
        else p.delete('module');
        return p;
      },
      { replace: true },
    );
  const submit = () => {
    const q = draft.trim();
    if (q && q === query) void results.refetch();
    else setQuery(q);
  };

  const { data, error } = results;
  return (
    <main className="flex min-h-[480px] flex-1 flex-col md:flex-row">
      <section aria-label="Search" className="flex-none border-b bg-card md:relative md:w-[520px] md:border-r md:border-b-0 min-[1300px]:w-[600px]">
        <div className="flex flex-col md:absolute md:inset-0">
          <div className="flex flex-col gap-3 border-b p-4">
            <form
              role="search"
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                submit();
              }}
            >
              <label className="flex h-8 min-w-0 flex-1 items-center gap-2 rounded-sm border border-input bg-card px-2 text-sm has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-ring">
                <MagnifyingGlassIcon size={16} aria-hidden className="flex-none text-muted-foreground" />
                <input
                  type="search"
                  value={draft}
                  maxLength={500}
                  onChange={(event) => setDraft(event.target.value)}
                  aria-label="Search the code"
                  placeholder="Search the code"
                  className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
                />
              </label>
              <div role="group" aria-label="Search mode" className="flex h-8 flex-none overflow-hidden rounded-md border border-input">
                {MODES.map(([m, label]) => (
                  <button
                    key={m}
                    type="button"
                    aria-pressed={m === mode}
                    onClick={() => setMode(m)}
                    className="border-input px-3 text-sm font-medium text-muted-foreground transition-colors not-first:border-l focus-visible:outline-2 focus-visible:-outline-offset-4 focus-visible:outline-current aria-pressed:bg-foreground aria-pressed:text-card"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </form>
            {data && (
              <div role="status" className="flex items-center gap-2 text-sm">
                {data.hits.length === 1 ? '1 result' : `${data.hits.length} results`}
                {data.mode_used === 'hybrid' ? (
                  <Tooltip>
                    <TooltipTrigger className="ml-auto inline-flex h-6 items-center gap-1 rounded-sm bg-neutral-tint px-2 whitespace-nowrap text-neutral">
                      <InfoIcon size={16} aria-hidden />
                      {data.native_hybrid ? 'Native Atlas hybrid' : 'App-side fusion'}
                    </TooltipTrigger>
                    <TooltipContent side="bottom">
                      {data.native_hybrid
                        ? 'Atlas merged the keyword and vector rankings with $rankFusion.'
                        : 'This Atlas can’t run $rankFusion, so the app merged the keyword and vector rankings.'}
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  data.mode_used !== mode && (
                    <span className="ml-auto text-muted-foreground">Vector search is unavailable, so these are keyword results only.</span>
                  )
                )}
              </div>
            )}
          </div>
          <div className="md:min-h-0 md:flex-1 md:overflow-y-auto">
            {!query ? (
              <p className="p-4 text-sm text-muted-foreground">
                Find code by keyword, by meaning (vector), or both (hybrid), then press Enter. Pick a result to see its module on the
                graph.
              </p>
            ) : error instanceof ApiError && error.code === 'SEARCH_INDEX_NOT_READY' ? (
              <NotReadyNotice error={error} onKeyword={mode === 'keyword' ? undefined : () => setMode('keyword')} />
            ) : error ? (
              <p className="p-4 text-sm">Couldn’t search: {error.message}</p>
            ) : !data ? (
              <p className="p-4 text-sm text-muted-foreground">Searching…</p>
            ) : !data.hits.length ? (
              <p className="p-4 text-sm text-muted-foreground">Nothing matches “{query}”.</p>
            ) : (
              <ol>
                {data.hits.map((hit) => (
                  <li key={hit.chunk_id}>
                    <Hit
                      hit={hit}
                      words={words}
                      picked={hit.chunk_id === picked && hit.module_id === module}
                      onPick={() => {
                        setPicked(hit.chunk_id);
                        select(hit.module_id);
                      }}
                    />
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </section>
      <GraphArea graph={graph} selected={module} filter="" onSelect={select} />
    </main>
  );
}

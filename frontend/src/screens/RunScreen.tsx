import { CircleIcon, ListChecksIcon, XCircleIcon } from '@phosphor-icons/react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { cn } from 'cn';
import { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useOutletContext, useParams, useSearchParams } from 'react-router-dom';

import { ApiError, cancelRun, getGraph, getPlan, listRunEvents } from '@/api/client';
import { ConnectionBanner } from '@/components/ConnectionBanner';
import { Button, buttonVariants } from '@/components/ui/button';
import { isLive, POLL_MS, useRun } from '@/lib/run';
import { RUN_STATE, TONE_BORDER, TONE_TEXT, TONE_TINT } from '@/lib/status';
import { GraphArea } from '@/screens/GraphScreen';
import { Field } from '@/screens/Overview';
import type { RunEvent, RunSummary } from '@/types/contracts';

const FAIL = new Set(['verification_failed', 'patch_rejected', 'unit_blocked', 'error']);
// worker.py turns the run terminal first, then records report_generated or an error event.
const CLOSING = new Set(['report_generated', 'error']);
// ponytail: a run that ends with no closing event (a backend restart) stops being polled after this.
const CLOSING_WAIT_MS = 120_000;
const time = (iso: string) => new Date(iso).toLocaleTimeString('en-GB');

// ponytail: generic payload flattening; step 4 gives tool calls, turns and gates their own rows.
function describe(e: RunEvent, unit: (id: string) => string) {
  const p = e.payload;
  const detail =
    typeof p.from === 'string' && typeof p.to === 'string'
      ? `${p.from} to ${p.to}`
      : Object.values(p).filter((v) => typeof v === 'string' || typeof v === 'number').join(', ');
  return [e.unit_id && unit(e.unit_id), detail, e.attempt && `attempt ${e.attempt}`].filter(Boolean).join(', ');
}

/** Spec §9.3: fetch only what is after the last sequence held, and drop anything already seen. */
function useRunEvents(run?: RunSummary) {
  const qc = useQueryClient();
  const runId = run?.run_id;
  const key = ['run-events', runId];
  return useQuery({
    queryKey: key,
    queryFn: async () => {
      const prev = qc.getQueryData<RunEvent[]>(key) ?? [];
      const last = prev.at(-1)?.sequence ?? 0;
      const next = (await listRunEvents(runId!, last)).filter((e) => e.sequence > last);
      return next.length ? [...prev, ...next] : prev;
    },
    enabled: Boolean(runId),
    refetchInterval: (q) => (run && !settled(run, q.state.data ?? []) ? POLL_MS : false),
  });
}

/** Finished, and its closing event has arrived (or never will). Until then the log keeps polling. */
function settled(run: RunSummary, log: RunEvent[]) {
  const last = log.at(-1);
  if (isLive(run) || (last?.sequence ?? 0) < run.last_event_sequence) return false;
  // A failed run carries its reason in run.error, which a restart-interrupted run gets with no closing event.
  return CLOSING.has(last?.event_type ?? '') || Boolean(run.error) || Date.now() - Date.parse(run.updated_at) > CLOSING_WAIT_MS;
}

function Empty({ repoId, search }: { repoId: string; search: string }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
      <ListChecksIcon size={24} aria-hidden className="text-muted-foreground" />
      <h2 className="text-xl leading-tight font-semibold">No migration running</h2>
      <p className="max-w-[44ch] text-muted-foreground">Approve a plan to start one. Unit states and tool calls appear here as the run records them.</p>
      <Link to={{ pathname: `/repos/${encodeURIComponent(repoId)}/plan`, search }} className={cn(buttonVariants(), 'mt-2')}>
        Go to plan
      </Link>
    </main>
  );
}

function Dashboard({ repoId, run }: { repoId: string; run: RunSummary }) {
  const qc = useQueryClient();
  const live = isLive(run);
  const events = useRunEvents(run);
  const listening = !settled(run, events.data ?? []);
  const graph = useQuery({
    queryKey: ['graph', repoId, run.run_id],
    queryFn: () => getGraph(repoId, run.run_id),
    refetchInterval: live ? POLL_MS : false,
  });
  const plan = useQuery({ queryKey: ['plan', run.plan_id], queryFn: () => getPlan(run.plan_id) });
  const cancel = useMutation({
    mutationFn: () => cancelRun(run.run_id),
    onSuccess: (r) => qc.setQueryData(['run', r.run_id], r),
  });

  const paths = new Map(plan.data?.units.map((u) => [u.unit_id, u.file_paths.join(', ')]));
  const unit = (id: string) => paths.get(id) ?? id;
  const current = run.units.find((u) => u.unit_id === run.current_unit);
  // The graph follows the run's current unit until someone picks a module.
  const [picked, setPicked] = useState<string | null>();
  const [confirming, setConfirming] = useState(false);
  const cancelButton = useRef<HTMLButtonElement>(null);
  const log = events.data ?? [];
  const last = log.at(-1);
  const tests = run.tests_passed + run.tests_failed + run.tests_inconclusive;
  const { icon: StateIcon, label: state, tone } = RUN_STATE[run.state];

  return (
    <>
      <div className="flex min-h-14 flex-none flex-wrap items-center gap-x-8 gap-y-2 border-b bg-card px-4 py-2">
        <span className={cn('inline-flex h-8 items-center gap-2 rounded-md border px-3 text-base font-medium whitespace-nowrap', TONE_TINT[tone], TONE_TEXT[tone], TONE_BORDER[tone])}>
          <StateIcon size={20} aria-hidden />
          {state}
        </span>
        <Field label="Current unit">
          {current ? <span className="font-mono font-medium">{unit(current.unit_id)}</span> : <span className="text-muted-foreground">{live ? 'None yet' : 'None'}</span>}
        </Field>
        {/* attempts counts submitted patches, so it reads 0 while the first one is being written. */}
        <Field label="Attempt">{current ? Math.max(current.attempts, 1) : '–'}</Field>
        <Field label="Tests">
          {tests ? `${run.tests_passed} passed, ${run.tests_failed} failed${run.tests_inconclusive ? `, ${run.tests_inconclusive} inconclusive` : ''}` : 'Not run yet'}
        </Field>
        <Field label="Last event">{last ? `${time(last.timestamp)}, event ${last.sequence}` : 'None yet'}</Field>
        {live && (
          <div className="ml-auto flex items-center gap-2">
            {confirming && (
              <>
                <span className="text-sm text-muted-foreground">Stops after the current step. Verified units stay verified.</span>
                <Button
                  variant="outline"
                  onClick={() => {
                    setConfirming(false);
                    cancelButton.current?.focus();
                  }}
                >
                  Keep running
                </Button>
              </>
            )}
            {/* Stays mounted while confirming, so keyboard focus stays on it. */}
            <Button
              ref={cancelButton}
              variant={confirming ? 'destructive' : 'outline'}
              // The API only sets a flag; the worker stops at its next step, which can be a minute away.
              disabled={!cancel.isIdle && !cancel.isError}
              onClick={() => {
                setConfirming(!confirming);
                if (confirming) cancel.mutate();
              }}
            >
              {confirming ? 'Yes, cancel run' : cancel.isIdle || cancel.isError ? 'Cancel run' : 'Cancelling…'}
            </Button>
          </div>
        )}
      </div>
      {(run.error || cancel.error) && (
        <div role="alert" className="flex flex-none items-center gap-2 border-b bg-failed-tint px-4 py-2 font-medium text-failed">
          <XCircleIcon size={20} aria-hidden className="flex-none" />
          {run.error ?? cancel.error?.message}
        </div>
      )}

      <div className="flex min-h-[480px] flex-1">
        <GraphArea graph={graph} selected={picked === undefined ? (current?.module_ids[0] ?? null) : picked} filter="" onSelect={setPicked} />
        <aside aria-label="Run events" className="relative w-[400px] flex-none border-l bg-card xl:w-[440px] min-[1300px]:w-[480px]">
          <div className="absolute inset-0 flex flex-col">
            <div className="flex flex-none items-baseline justify-between gap-3 border-b px-4 py-3">
              <h2 className="text-sm font-medium text-muted-foreground">Events</h2>
              <span className="text-sm text-muted-foreground">Newest at the bottom</span>
            </div>
            {/* column-reverse keeps the scroll pinned to the newest row as rows arrive; mb-auto keeps a short log at the top. */}
            {/* tabIndex: keyboard users scroll the log with the arrow keys (WCAG 2.1.1). */}
            <div
              role="log"
              tabIndex={0}
              aria-label="Run events, newest last"
              className="flex min-h-0 flex-1 flex-col-reverse overflow-y-auto focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring"
            >
              <div className="mb-auto">
                {events.isError && !log.length && <p className="px-4 py-3 text-sm text-muted-foreground">Couldn’t load the events: {events.error.message}</p>}
                {events.isSuccess && !log.length && <p className="px-4 py-3 text-sm text-muted-foreground">No events yet. The run records one at each step.</p>}
                {log.map((e) => {
                  const fail = FAIL.has(e.event_type);
                  const text = describe(e, unit);
                  return (
                    <div key={e.sequence} title={text} className={cn('flex h-9 items-center gap-2 border-b px-4 text-sm whitespace-nowrap', fail && 'bg-failed-tint')}>
                      {fail ? <XCircleIcon size={16} aria-hidden className="flex-none text-failed" /> : <CircleIcon size={16} aria-hidden className="flex-none text-muted-foreground" />}
                      <span className="font-mono text-muted-foreground">{time(e.timestamp)}</span>
                      <span className={cn('font-mono font-medium', fail && 'text-failed')}>{e.event_type}</span>
                      <span className="min-w-0 flex-1 truncate text-muted-foreground">{text}</span>
                    </div>
                  );
                })}
              </div>
            </div>
            <p className="flex-none border-t px-4 py-3 text-sm text-muted-foreground">
              {listening ? 'Checking for new events every 1.5 s.' : `Run ${state.toLowerCase()}. No more events will arrive.`}
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}

/** 06 Run dashboard. Template: kit.js s06. The run id lives in ?run=, set by Start migration on the plan screen. */
export default function RunScreen() {
  const { repoId = '' } = useParams();
  const [params] = useSearchParams();
  const navSlot = useOutletContext<HTMLElement | null>();
  const runId = params.get('run');
  const run = useRun(runId);
  // A status code means the API answered; only a network failure is a lost connection.
  const lost = run.error instanceof ApiError && run.error.status === 0;

  if (!runId) return <Empty repoId={repoId} search={params.size ? `?${params}` : ''} />;
  return (
    <main className="flex flex-1 flex-col">
      {navSlot &&
        createPortal(
          <span className="text-sm whitespace-nowrap text-muted-foreground">
            Run ID <span className="font-mono text-foreground">{runId}</span>
          </span>,
          navSlot,
        )}
      {lost && (
        <ConnectionBanner
          note="Retrying every 1.5 s. Everything below is from that time."
          lastOk={run.data ? run.dataUpdatedAt : undefined}
          retrying={run.isFetching}
          onRetry={() => void run.refetch()}
        />
      )}
      {run.data ? (
        <Dashboard repoId={repoId} run={run.data} />
      ) : (
        !lost && <p className="p-6 text-muted-foreground">{run.isError ? `Couldn’t load this run: ${run.error.message}` : 'Loading the run…'}</p>
      )}
    </main>
  );
}

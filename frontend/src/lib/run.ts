import { useQuery } from '@tanstack/react-query';

import { getRun } from '@/api/client';
import type { RunState, RunSummary } from '@/types/contracts';

/** Spec §9.3: poll every 1.5 s, and only while the run is non-terminal. */
export const POLL_MS = 1500;
const TERMINAL: ReadonlySet<RunState> = new Set(['completed', 'completed_with_warnings', 'failed', 'cancelled']);
export const isLive = (run?: RunSummary) => !run || !TERMINAL.has(run.state);

/** One query per run, shared by the app bar's progress and the run screen. A failed poll keeps the last data. */
export function useRun(runId: string | null) {
  return useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId!),
    enabled: Boolean(runId),
    refetchInterval: (q) => (isLive(q.state.data) ? POLL_MS : false),
  });
}

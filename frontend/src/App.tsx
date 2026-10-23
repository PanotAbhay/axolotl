/**
 * App shell - owner: Dev 5. Layout and copy follow the UI template in docs/design/.
 *
 * The system status chips sit in the app bar on every screen: they are how the team sees at a
 * glance whether Atlas, the runner and Gemini are wired. Status is never faked: with no
 * response there are no chips, only the connection banner.
 *
 * Ids live in the URL because no endpoint lists a repository's runs:
 * /repos/:repoId/<tab>, with ?plan= and ?run= carried from tab to tab.
 */

import { WifiSlashIcon } from '@phosphor-icons/react';
import { useQuery } from '@tanstack/react-query';
import { cn } from 'cn';
import { lazy, Suspense, useState } from 'react';
import { Link, NavLink, Outlet, Route, Routes, useMatch, useParams, useSearchParams } from 'react-router-dom';

import { API_BASE, getSystemStatus } from '@/api/client';
import { AppBar } from '@/components/AppBar';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import NewMigration from '@/screens/NewMigration';
import Overview from '@/screens/Overview';

const STATUS_POLL_MS = 5000;
// import.meta.env.DEV is false in `npm run build`, so the preview is dropped from production.
const UiPreview = import.meta.env.DEV ? lazy(() => import('@/dev/UiPreview')) : null;
// React Flow and dagre load with the graph, not on every screen.
const GraphScreen = lazy(() => import('@/screens/GraphScreen'));

function ConnectionBanner({ lastOk, retrying, onRetry }: { lastOk?: number; retrying: boolean; onRetry: () => void }) {
  return (
    <div role="status" className="flex min-h-12 flex-none flex-wrap items-center gap-x-3 gap-y-1 border-b border-border-strong bg-muted px-4 py-2">
      <WifiSlashIcon size={20} aria-hidden />
      {lastOk ? (
        <>
          <span className="font-medium">Connection lost — last known status at {new Date(lastOk).toLocaleTimeString('en-GB')}</span>
          <span className="text-sm text-muted-foreground">Retrying every 5 s. The status chips are from that time.</span>
        </>
      ) : (
        <>
          <span className="font-medium">Can’t reach the API at {API_BASE}</span>
          <span className="text-sm text-muted-foreground">
            Start it with <code className="font-mono">cd backend && uv run uvicorn app.main:app --port 8000</code>
          </span>
        </>
      )}
      <Button variant="outline" className="ml-auto" onClick={onRetry} disabled={retrying}>
        {retrying ? 'Retrying…' : 'Retry now'}
      </Button>
    </div>
  );
}

function Shell() {
  const repoId = useMatch('/repos/:repoId/*')?.params.repoId;
  const status = useQuery({ queryKey: ['system-status'], queryFn: getSystemStatus, refetchInterval: STATUS_POLL_MS });
  return (
    <div className="flex min-h-svh flex-col">
      <AppBar repoId={repoId} status={status.data} />
      {status.isError && (
        <ConnectionBanner
          lastOk={status.data ? status.dataUpdatedAt : undefined}
          retrying={status.isFetching}
          onRetry={() => void status.refetch()}
        />
      )}
      <Outlet />
    </div>
  );
}

const TABS = [
  { label: 'Overview', path: '' },
  { label: 'Graph', path: '/graph' },
  { label: 'Plan', path: '/plan' },
  { label: 'Run', path: '/run', needsRun: true },
  { label: 'Report', path: '/report', needsRun: true },
  { label: 'Search', path: '/search' },
];
const TAB = 'flex items-center px-3 text-sm font-medium border-b-2 border-transparent -mb-px transition-colors';

function RepoLayout() {
  const { repoId = '' } = useParams();
  const [params] = useSearchParams();
  const search = params.size ? `?${params}` : '';
  // A screen can put controls at the right of the tab bar (the graph's filter) through this slot.
  const [navSlot, setNavSlot] = useState<HTMLDivElement | null>(null);
  return (
    <>
      <nav aria-label="Repository" className="flex h-10 flex-none items-stretch gap-4 border-b bg-card px-4">
        <div className="flex gap-1 overflow-x-auto">
          {TABS.map(({ label, path, needsRun }) =>
            needsRun && !params.get('run') ? (
              <Tooltip key={label}>
                <TooltipTrigger aria-disabled="true" className={cn(TAB, 'cursor-not-allowed text-border-strong')}>
                  {label}
                </TooltipTrigger>
                <TooltipContent side="bottom">Start a migration from the Plan tab first.</TooltipContent>
              </Tooltip>
            ) : (
              <NavLink
                key={label}
                to={{ pathname: `/repos/${encodeURIComponent(repoId)}${path}`, search }}
                end
                className={({ isActive }) =>
                  cn(TAB, isActive ? 'border-foreground text-foreground' : 'text-muted-foreground hover:text-foreground')
                }
              >
                {label}
              </NavLink>
            ),
          )}
        </div>
        <div ref={setNavSlot} className="ml-auto flex items-center" />
      </nav>
      <Outlet context={navSlot} />
    </>
  );
}

// ponytail: placeholder until each screen lands (steps 2-6); delete with the last one.
function Pending({ screen }: { screen: string }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
      <h1 className="text-2xl leading-tight font-semibold">{screen}</h1>
      <p className="text-muted-foreground">This screen isn’t built yet.</p>
    </main>
  );
}

function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
      <h1 className="text-2xl leading-tight font-semibold">No page at this address</h1>
      <Link to="/" className="underline underline-offset-4">
        Start a new migration
      </Link>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<NewMigration />} />
        <Route path="repos/:repoId" element={<RepoLayout />}>
          <Route index element={<Overview />} />
          <Route path="graph" element={<Suspense><GraphScreen /></Suspense>} />
          <Route path="plan" element={<Pending screen="Target and plan" />} />
          <Route path="run" element={<Pending screen="Run" />} />
          <Route path="report" element={<Pending screen="Final report" />} />
          <Route path="search" element={<Pending screen="Search" />} />
        </Route>
        {UiPreview && <Route path="dev/ui" element={<Suspense><UiPreview /></Suspense>} />}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

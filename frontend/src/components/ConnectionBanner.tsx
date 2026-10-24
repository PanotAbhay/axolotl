import { WifiSlashIcon } from '@phosphor-icons/react';

import { API_BASE } from '@/api/client';
import { Button } from '@/components/ui/button';

/** Spec §9.3: a failed poll keeps the last data on screen and says when it is from. `note` says what is stale. */
export function ConnectionBanner({ lastOk, note, retrying, onRetry }: { lastOk?: number; note: string; retrying: boolean; onRetry: () => void }) {
  return (
    <div role="status" className="flex min-h-12 flex-none flex-wrap items-center gap-x-3 gap-y-1 border-b border-border-strong bg-muted px-4 py-2">
      <WifiSlashIcon size={20} aria-hidden />
      {lastOk ? (
        <>
          <span className="font-medium">Connection lost — last known status at {new Date(lastOk).toLocaleTimeString('en-GB')}</span>
          <span className="text-sm text-muted-foreground">{note}</span>
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

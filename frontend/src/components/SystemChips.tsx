import { CheckCircleIcon, HourglassIcon, XCircleIcon } from '@phosphor-icons/react';
import { cn } from 'cn';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { chipsFor } from '@/lib/status';
import type { SystemStatus } from '@/types/contracts';

const ICON = { ok: CheckCircleIcon, building: HourglassIcon, unavailable: XCircleIcon };
// Colour only marks a problem; "ok" stays grey. The icon and the word carry the state without colour.
const CHIP = { ok: '', building: 'bg-working-tint', unavailable: 'bg-failed-tint' };
const ACCENT = { ok: 'text-muted-foreground', building: 'text-working', unavailable: 'text-failed' };

/** App bar chips from a real GET /system/status response. The shell renders none while there is no response. */
export function SystemChips({ status }: { status: SystemStatus }) {
  return (
    <ul className="flex flex-wrap items-center gap-2" aria-label="System status">
      {chipsFor(status).map(({ name, state, detail }) => {
        const Icon = ICON[state];
        return (
          <li key={name}>
            <Tooltip>
              <TooltipTrigger
                className={cn('inline-flex h-6 items-center gap-1 rounded-sm px-2 text-sm whitespace-nowrap', CHIP[state])}
              >
                <Icon size={16} className={ACCENT[state]} aria-hidden />
                <span>{name}</span>
                <span className={ACCENT[state]}>{state}</span>
              </TooltipTrigger>
              <TooltipContent side="bottom">{detail}</TooltipContent>
            </Tooltip>
          </li>
        );
      })}
    </ul>
  );
}

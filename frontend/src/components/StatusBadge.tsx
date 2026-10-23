import { cn } from 'cn';

import { TONE_TEXT, TONE_TINT, UNIT_STATUS } from '@/lib/status';
import type { UnitStatus } from '@/types/contracts';

/** A unit's state as icon plus word on its tint. Template: kit.js `badge`. */
export function StatusBadge({ status }: { status: UnitStatus }) {
  const { icon: Icon, label, tone } = UNIT_STATUS[status];
  return (
    <span className={cn('inline-flex h-6 items-center gap-1 rounded-sm px-2 text-sm whitespace-nowrap', TONE_TINT[tone], TONE_TEXT[tone])}>
      <Icon size={16} aria-hidden />
      {label}
    </span>
  );
}

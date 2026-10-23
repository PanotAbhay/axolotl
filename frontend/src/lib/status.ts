import {
  ArrowBendDownRightIcon,
  ArrowClockwiseIcon,
  CheckCircleIcon,
  CircleDashedIcon,
  CircleHalfIcon,
  CircleIcon,
  HourglassIcon,
  PencilSimpleIcon,
  ProhibitIcon,
  XCircleIcon,
  type Icon,
} from '@phosphor-icons/react';

import type { DependencyStatus, SystemStatus, UnitStatus } from '@/types/contracts';

export type Tone = 'neutral' | 'working' | 'repairing' | 'passed' | 'failed';

/** Spec §9.3: every unit state shows an icon and a word, never colour alone. Template: kit.js `ST`. */
export const UNIT_STATUS: Record<UnitStatus, { icon: Icon; label: string; tone: Tone }> = {
  not_planned: { icon: CircleDashedIcon, label: 'Not planned', tone: 'neutral' },
  queued: { icon: CircleIcon, label: 'Queued', tone: 'neutral' },
  baselining: { icon: CircleHalfIcon, label: 'Baselining', tone: 'working' },
  migrating: { icon: PencilSimpleIcon, label: 'Migrating', tone: 'working' },
  verifying: { icon: HourglassIcon, label: 'Verifying', tone: 'working' },
  repairing: { icon: ArrowClockwiseIcon, label: 'Repairing', tone: 'repairing' },
  passed: { icon: CheckCircleIcon, label: 'Passed', tone: 'passed' },
  blocked: { icon: ProhibitIcon, label: 'Blocked', tone: 'failed' },
  failed: { icon: XCircleIcon, label: 'Failed', tone: 'failed' },
  skipped: { icon: ArrowBendDownRightIcon, label: 'Skipped', tone: 'neutral' },
};

// Whole class names, so Tailwind's scanner finds them. Neutral states get the strong border, as in the template.
export const TONE_TEXT: Record<Tone, string> = {
  neutral: 'text-neutral', working: 'text-working', repairing: 'text-repairing', passed: 'text-passed', failed: 'text-failed',
};
export const TONE_TINT: Record<Tone, string> = {
  neutral: 'bg-neutral-tint', working: 'bg-working-tint', repairing: 'bg-repairing-tint', passed: 'bg-passed-tint', failed: 'bg-failed-tint',
};
export const TONE_BORDER: Record<Tone, string> = {
  neutral: 'border-border-strong', working: 'border-working', repairing: 'border-repairing', passed: 'border-passed', failed: 'border-failed',
};

export interface StatusChip {
  name: string;
  state: DependencyStatus;
  detail: string;
}

const RANK: DependencyStatus[] = ['ok', 'building', 'unavailable'];
const worst = (a: DependencyStatus, b: DependencyStatus) => (RANK.indexOf(b) > RANK.indexOf(a) ? b : a);

/** The four app bar chips from GET /system/status. The two search indexes share one chip showing the worse state. */
export function chipsFor(status: SystemStatus): StatusChip[] {
  const d = status.details ?? {};
  const { keyword, vector } = status.search_indexes;
  return [
    { name: 'MongoDB', state: status.mongodb, detail: d.mongodb ?? (d.mongodb_version ? `Version ${d.mongodb_version}.` : 'Connected.') },
    { name: 'Search indexes', state: worst(keyword, vector), detail: `Keyword index ${keyword}, vector index ${vector}.` },
    { name: 'Runner', state: status.runner.available ? 'ok' : 'unavailable', detail: d.runner ?? `Mode: ${status.runner.mode}.` },
    { name: 'Gemini', state: status.gemini.reachable ? 'ok' : 'unavailable', detail: d.gemini ?? `Model: ${status.gemini.model}.` },
  ];
}

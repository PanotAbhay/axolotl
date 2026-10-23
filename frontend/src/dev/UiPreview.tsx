/**
 * Dev-only component preview at /dev/ui, for checking shadcn components against the template's
 * Components view (docs/design/index.html#components). Not in production builds.
 */

import { ArrowRightIcon, DownloadSimpleIcon, MoonIcon } from '@phosphor-icons/react';
import type { ReactNode } from 'react';

import { SystemChips } from '@/components/SystemChips';
import { Button } from '@/components/ui/button';
import type { SystemStatus } from '@/types/contracts';

// Sample status so every chip state shows at once. Never used outside this page.
const SAMPLE: SystemStatus = {
  mongodb: 'ok',
  search_indexes: { keyword: 'ok', vector: 'building' },
  runner: { mode: 'docker', available: false },
  gemini: { model: 'gemini-4-argon', reachable: true },
  details: { runner: 'Docker daemon unreachable.' },
};

function Row({ name, note, children }: { name: string; note: string; children: ReactNode }) {
  return (
    <section className="grid gap-4 border-t py-6 md:grid-cols-[260px_minmax(0,1fr)]">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl leading-tight font-semibold">{name}</h2>
        <p className="text-sm text-muted-foreground">{note}</p>
      </div>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-4">{children}</div>
    </section>
  );
}

function Labelled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2">
      {children}
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  );
}

export default function UiPreview() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-2 px-4 py-8">
      <h1 className="text-2xl leading-tight font-semibold">Component preview</h1>
      <p className="mb-4 max-w-prose text-muted-foreground">
        Dev only. Hover to see hover states, press Tab to see focus, and use the header toggle for dark.
      </p>
      <Row name="Buttons" note="shadcn variant names. Template primary = default, secondary = outline.">
        <Labelled label="default (primary)"><Button>Approve plan</Button></Labelled>
        <Labelled label="outline (secondary)"><Button variant="outline">Retry now</Button></Labelled>
        <Labelled label="ghost"><Button variant="ghost">Cancel</Button></Labelled>
        <Labelled label="disabled"><Button disabled>Start migration</Button></Labelled>
        <Labelled label="with icons">
          <Button variant="outline"><DownloadSimpleIcon aria-hidden data-icon="inline-start" />Patch</Button>
        </Labelled>
        <Labelled label="icon trailing">
          <Button>Start migration<ArrowRightIcon aria-hidden data-icon="inline-end" /></Button>
        </Labelled>
        <Labelled label="icon (ghost)">
          <Button variant="ghost" size="icon" aria-label="Use dark theme"><MoonIcon size={20} aria-hidden /></Button>
        </Labelled>
      </Row>
      <Row name="Status chips" note="Sample data: one of each state. Hover or focus a chip for the reason.">
        <SystemChips status={SAMPLE} />
      </Row>
    </main>
  );
}

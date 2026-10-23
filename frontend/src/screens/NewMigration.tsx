import { InfoIcon, XCircleIcon } from '@phosphor-icons/react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { cn } from 'cn';
import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { importRepository, listDemoFixtures } from '@/api/client';
import { Button } from '@/components/ui/button';

const ZIP = 'zip';

/** One radio row. The checked row gets the ink outline; an error on it turns the outline red. */
function Choice({ value, checked, onPick, title, error, children }: {
  value: string;
  checked: boolean;
  onPick: (value: string) => void;
  title: ReactNode;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-3 rounded-md border border-input bg-card px-4 py-3 has-checked:outline-2 has-checked:-outline-offset-2',
        error ? 'has-checked:outline-failed' : 'has-checked:outline-foreground',
        'has-focus-visible:ring-2 has-focus-visible:ring-ring has-focus-visible:ring-offset-2 has-focus-visible:ring-offset-background',
      )}
    >
      <label className="flex cursor-pointer items-start gap-3">
        <input type="radio" name="source" value={value} checked={checked} onChange={() => onPick(value)} className="peer sr-only" />
        <span
          aria-hidden
          className="mt-0.5 flex size-5 flex-none items-center justify-center rounded-full border border-input bg-card peer-checked:border-2 peer-checked:border-foreground peer-checked:after:size-2.5 peer-checked:after:rounded-full peer-checked:after:bg-foreground peer-checked:after:content-['']"
        />
        <span className="flex min-w-0 flex-col">
          <span className="font-medium">{title}</span>
          {error ? (
            <span role="alert" className="flex items-center gap-1 font-medium text-failed">
              <XCircleIcon size={16} aria-hidden className="flex-none" />
              {error}
            </span>
          ) : null}
          <span className="text-muted-foreground">{children}</span>
        </span>
      </label>
    </div>
  );
}

/** 01 New migration: import the demo fixture or a ZIP. Errors are the API's own, on the choice they're about. */
export default function NewMigration() {
  const navigate = useNavigate();
  const fixtures = useQuery({ queryKey: ['demo-fixtures'], queryFn: listDemoFixtures });
  const [picked, setPicked] = useState<string>();
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const source = picked ?? fixtures.data?.[0]?.demo_fixture_id ?? ZIP;
  const fixture = fixtures.data?.find((f) => f.demo_fixture_id === source);

  const run = useMutation({
    mutationFn: () => importRepository(source === ZIP ? file! : { demo_fixture_id: source }, name.trim() || undefined),
    onSuccess: (record) => navigate(`/repos/${encodeURIComponent(record.repository_id)}`),
  });
  const pick = (value: string) => {
    setPicked(value);
    run.reset();
  };
  // Picking another source clears the error, so any error is about the source still picked.
  const errorOn = (value: string) => (run.isError && source === value ? run.error.message : undefined);

  return (
    <main className="mx-auto flex w-full max-w-[640px] flex-col gap-6 px-4 pt-8 pb-16 [@media(min-height:800px)]:pt-16">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl leading-tight font-semibold">New migration</h1>
        <p className="text-muted-foreground">
          Import a Python project. Axolotl maps its modules and imports, then migrates and verifies one unit at a time.
        </p>
      </div>
      <div className="flex items-start gap-2 rounded-md border bg-card px-4 py-3">
        <InfoIcon size={20} aria-hidden className="flex-none text-muted-foreground" />
        <span>Uploads are analysed statically and never run. Only trusted demo fixtures can be migrated.</span>
      </div>

      <form
        className="flex flex-col gap-6"
        onSubmit={(event) => {
          event.preventDefault();
          run.mutate();
        }}
      >
        <fieldset className="flex flex-col gap-2" disabled={run.isPending}>
          <legend className="mb-2 text-sm font-medium text-muted-foreground">Source</legend>
          {fixtures.isError && (
            <p className="text-sm text-muted-foreground">Couldn’t load the demo fixtures: {fixtures.error.message}</p>
          )}
          {fixtures.data?.map((f) => (
            <Choice
              key={f.demo_fixture_id}
              value={f.demo_fixture_id}
              checked={source === f.demo_fixture_id}
              onPick={pick}
              error={errorOn(f.demo_fixture_id)}
              title={<>Demo fixture: <span className="font-mono text-sm">{f.name}</span></>}
            >
              {f.description} Trusted, so it can run in the sandbox.
            </Choice>
          ))}
          <Choice value={ZIP} checked={source === ZIP} onPick={pick} error={errorOn(ZIP)} title="Upload a ZIP">
            Up to 10 MB and 500 files. Static analysis only, so it can’t be migrated.
          </Choice>
          {source === ZIP && (
            <label className="flex flex-col gap-2 pt-2">
              <span className="text-sm font-medium text-muted-foreground">Archive</span>
              <input
                type="file"
                accept=".zip,application/zip"
                required
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  run.reset();
                }}
                className="text-sm file:mr-3 file:h-8 file:rounded-md file:border file:border-input file:bg-card file:px-3 file:font-medium file:text-foreground hover:file:bg-muted"
              />
            </label>
          )}
        </fieldset>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-muted-foreground">Project name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={source === ZIP ? (file?.name.replace(/\.zip$/i, '') ?? 'Name of the ZIP file') : fixture?.name}
            disabled={run.isPending}
            className="h-8 w-full max-w-80 rounded-sm border border-input bg-card px-2 font-mono text-sm placeholder:text-muted-foreground"
          />
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={run.isPending}>
            {run.isPending ? 'Importing…' : 'Import repository'}
          </Button>
          {run.isPending && (
            <span role="status" className="text-sm text-muted-foreground">
              Mapping modules and imports. With search indexing on, this can take a minute.
            </span>
          )}
        </div>
      </form>
    </main>
  );
}

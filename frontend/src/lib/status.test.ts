import { describe, expect, it } from 'vitest';

import type { SystemStatus } from '@/types/contracts';

import { chipsFor } from './status';

const base: SystemStatus = {
  mongodb: 'ok',
  search_indexes: { keyword: 'ok', vector: 'ok' },
  runner: { mode: 'docker', available: true },
  gemini: { model: 'gemini-3.8-flash', reachable: true },
};

const states = (s: SystemStatus) => chipsFor(s).map((c) => `${c.name}: ${c.state}`);

describe('chipsFor', () => {
  it('shows four chips, all ok', () => {
    expect(states(base)).toEqual(['MongoDB: ok', 'Search indexes: ok', 'Runner: ok', 'Gemini: ok']);
  });

  it('gives the search chip the worse of the two indexes', () => {
    expect(chipsFor({ ...base, search_indexes: { keyword: 'ok', vector: 'building' } })[1].state).toBe('building');
    expect(chipsFor({ ...base, search_indexes: { keyword: 'unavailable', vector: 'building' } })[1].state).toBe('unavailable');
  });

  it('marks an unavailable runner and Gemini, with the backend reason', () => {
    const chips = chipsFor({
      ...base,
      runner: { mode: 'docker', available: false },
      gemini: { model: 'gemini-3.8-flash', reachable: false },
      details: { runner: 'Docker daemon not running.' },
    });
    expect(chips[2]).toEqual({ name: 'Runner', state: 'unavailable', detail: 'Docker daemon not running.' });
    expect(chips[3].state).toBe('unavailable');
  });
});

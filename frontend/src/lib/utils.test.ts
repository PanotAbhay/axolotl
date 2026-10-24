import { describe, expect, it } from 'vitest';

import { scopedSearch } from './utils';

describe('scopedSearch', () => {
  it('keeps the run and plan, drops a screen’s own params', () => {
    expect(scopedSearch(new URLSearchParams('plan=p1&run=r1&module=m&unit=u&path=a.py'))).toBe('?plan=p1&run=r1');
  });

  it('is empty when there is nothing to carry', () => {
    expect(scopedSearch(new URLSearchParams('module=m'))).toBe('');
  });
});

import { describe, expect, it } from 'vitest';

import { excerpt, queryWords, splitAtWords } from './search';

describe('search snippets', () => {
  it('marks the query words, not filler or punctuation', () => {
    const words = queryWords('Where is the bill ROUNDED? round');
    expect(words).toEqual(['bill', 'rounded', 'round']);
    expect(splitAtWords('total = Round(bill)', words)).toEqual(['total = ', 'Round', '(', 'bill', ')']);
    expect(splitAtWords('a.*b', [])).toEqual(['a.*b']);
  });

  it('starts the excerpt just above the first matching line', () => {
    const snippet = ['def price():', '    """Docs."""', '    taxed = tax()', '    return round(taxed)', '    # end', '    # more'].join('\n');
    expect(excerpt(snippet, ['round'])).toBe(['    taxed = tax()', '    return round(taxed)', '    # end', '    # more'].join('\n'));
    expect(excerpt(snippet, ['missing'], 2)).toBe('def price():\n    """Docs."""');
  });
});

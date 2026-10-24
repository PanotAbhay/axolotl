import { describe, expect, it } from 'vitest';

import { call, outcome, py } from './values';

describe('py', () => {
  it('writes §5-tagged values the way Python would', () => {
    expect(py({ __decimal__: '2.65' })).toBe('2.65');
    expect(py({ __tuple__: [1] })).toBe('(1,)');
    expect(py({ __set__: ['a', 'b'] })).toBe('{"a", "b"}');
    expect(py({ __dict_items__: [[1, null]] })).toBe('{1: None}');
    expect(py({ __object__: 'Line', fields: { sku: 'SKU-A', paid: true } })).toBe('Line(sku="SKU-A", paid=True)');
    expect(py({ total: { __decimal__: '1.50' }, lines: [] })).toBe('{"total": 1.50, "lines": []}');
  });
});

describe('outcome and call', () => {
  it('say how a case ended and what it was called with', () => {
    const base = { case_id: 'case_1', exception_type: null, exception_message: null, duration_ns: null };
    expect(outcome({ ...base, status: 'ok', value: { __decimal__: '2.64' } })).toBe('2.64');
    expect(outcome({ ...base, status: 'raised', value: null, exception_type: 'ValueError', exception_message: 'bad' })).toBe('raises ValueError: bad');
    expect(outcome({ ...base, status: 'timeout', value: null })).toBe('timed out');
    expect(call('pricing.line_gross', [{ __decimal__: '2.45' }, 1], { rounding: 'half_up' })).toBe('pricing.line_gross(2.45, 1, rounding="half_up")');
  });
});

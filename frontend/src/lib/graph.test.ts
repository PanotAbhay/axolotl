import { describe, expect, it } from 'vitest';

import { dependencyEdges, moduleRows } from '@/lib/graph';
import type { GraphEdge, GraphNode, GraphPayload } from '@/types/contracts';

const edge = (source: string, target: string, over: Partial<GraphEdge> = {}): GraphEdge => ({
  id: `${source}-${target}-${over.type ?? 'imports'}`,
  source,
  target,
  type: 'imports',
  resolution: 'confirmed',
  basis: 'static_ast',
  source_path: null,
  source_line: null,
  ...over,
});
const node = (id: string, kind: GraphNode['kind'] = 'local_module'): GraphNode => ({
  id,
  label: id,
  kind,
  path: kind === 'external_package' ? null : `${id}.py`,
  status: 'not_planned',
  unit_id: null,
  function_count: 1,
  class_count: 0,
  warnings: [],
});

describe('dependencyEdges', () => {
  it('draws one edge per pair, keeping the most certain resolution', () => {
    const edges = dependencyEdges([
      edge('tests', 'pricing', { resolution: 'heuristic' }),
      edge('tests', 'pricing', { type: 'test_targets' }),
      edge('orders', 'pricing', { resolution: 'unresolved' }),
    ]);
    expect(edges.map((e) => [e.source, e.resolution])).toEqual([
      ['tests', 'confirmed'],
      ['orders', 'unresolved'],
    ]);
  });
});

describe('moduleRows', () => {
  it('counts local imports and importers over unique pairs, and leaves out external packages', () => {
    const graph = {
      nodes: [node('orders'), node('pricing'), node('tests', 'test_module'), node('decimal', 'external_package')],
      edges: [
        edge('orders', 'pricing'),
        edge('orders', 'decimal'),
        edge('tests', 'pricing'),
        edge('tests', 'pricing', { type: 'test_targets' }),
      ],
    } as GraphPayload;
    expect(moduleRows(graph).map((r) => [r.id, r.localImports, r.importedBy])).toEqual([
      ['orders', 1, 0],
      ['pricing', 0, 2],
      ['tests', 1, 0],
    ]);
  });
});

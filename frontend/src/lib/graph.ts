import type { GraphEdge, GraphPayload, Resolution } from '@/types/contracts';

const STRENGTH: Resolution[] = ['unresolved', 'heuristic', 'confirmed'];

/**
 * One edge per importer -> dependency pair. The API sends `imports` and `test_targets` for the
 * same pair as separate edges; drawn twice they overlap. The pair keeps its most certain resolution.
 */
export function dependencyEdges(edges: GraphEdge[]): GraphEdge[] {
  const pairs = new Map<string, GraphEdge>();
  for (const edge of edges) {
    const key = `${edge.source}>${edge.target}`;
    const seen = pairs.get(key);
    if (!seen || STRENGTH.indexOf(edge.resolution) > STRENGTH.indexOf(seen.resolution)) pairs.set(key, edge);
  }
  return [...pairs.values()];
}

export interface ModuleRow {
  id: string;
  label: string;
  functions: number;
  classes: number;
  localImports: number;
  importedBy: number;
}

/** The Overview's module table: every node with a file, counted over unique pairs. */
export function moduleRows(graph: GraphPayload): ModuleRow[] {
  const edges = dependencyEdges(graph.edges);
  const local = new Set(graph.nodes.filter((n) => n.kind !== 'external_package').map((n) => n.id));
  return graph.nodes
    .filter((n) => n.path)
    .map((n) => ({
      id: n.id,
      label: n.label,
      functions: n.function_count,
      classes: n.class_count,
      localImports: edges.filter((e) => e.source === n.id && local.has(e.target)).length,
      importedBy: edges.filter((e) => e.target === n.id).length,
    }));
}

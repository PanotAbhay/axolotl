# cycles: T-05 fixture (Dev 3)

A tiny, never-executed package whose only job is to contain **real import cycles** for
T-05 ("cyclic dependency fixture: SCC detected and grouped/flagged"). It is parsed by
the same AST and graph code as any import; nothing here is ever run.

Expected module edges (A -> B means A imports B):

```
module_alpha      -> module_beta        import beta            cycle 1
module_beta       -> module_alpha       from alpha import ...  cycle 1
module_beta       -> module_leaf        import leaf
module_gamma      -> module_alpha       import alpha           depends on cycle 1
module_shop__cart -> module_shop__tax   from . import tax      cycle 2 (relative)
module_shop__tax  -> module_shop__cart  from .cart import ...  cycle 2 (relative)
```

`gamma` also calls `importlib.import_module("beta")`. That is recorded as an
`unknown_dynamic` edge and must never join or create a cycle: scheduling uses
confirmed static imports only.

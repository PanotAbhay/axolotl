# Demo inputs

- [`chess/`](chess/README.md): Will's terminal chess program, preserved unchanged.
  The refreshed source supports Python 2.7 and 3.14; the demo targets modernisation
  between those interpreters. Both runtime test suites pass. See the
  [integration notes](../docs/chess-demo.md) before using it as a migration fixture.
- [`legacy_orders/`](legacy_orders/README.md): existing executable Python 3 fixture.
- `challenge_cases/`: independent orders oracle, excluded from model context and
  source snapshots. It must not be reused as the chess oracle.

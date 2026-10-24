# Demo inputs

> **Decision, 24 Oct 2026:** the MVP demo is Will's chess game, migrated from Python 2.7 to Python 3.14.
> `legacy_orders` stays as the backup demo and must keep working. Chess can't be migrated yet:
> see [#30](https://github.com/Prittstick22/axolotl/issues/30) and [PROJECT_STATUS.md](../docs/PROJECT_STATUS.md).

- [`chess/`](chess/README.md): Will's terminal chess program, preserved unchanged.
  The refreshed source supports Python 2.7 and 3.14; the demo targets modernisation
  between those interpreters. Both runtime test suites pass. See the
  [integration notes](../docs/chess-demo.md) before using it as a migration fixture.
- [`legacy_orders/`](legacy_orders/README.md): existing executable Python 3 fixture, and the backup demo.
- `challenge_cases/`: independent orders oracle, excluded from model context and
  source snapshots. It must not be reused as the chess oracle.

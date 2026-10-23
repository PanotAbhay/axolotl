# Notes for Dev 1: chess 2.7 → 3.14, the runtime endpoint and the explorer

From Dev 5, 23 Oct 2026. These came up while folding your explorer into the main screens.
Item 2 blocks the chess demo. Items 1 and 3 are smaller.

## 1. The runtime endpoint returns 500 for repos imported on another machine

`GET /api/v1/repositories/{id}/runtime` reads the snapshot directory. Snapshots exist only
on the machine that imported them (`WORKSPACE_ROOT/snapshots/{repo_id}`), but the
repository record is in the shared Atlas database. On any other machine, `root.iterdir()`
in [runtime.py:14](../backend/app/ingestion/runtime.py) raises `FileNotFoundError` and the
API answers 500.

To reproduce, open a repo a teammate imported. The Overview's Python version panel shows
"Couldn't read the package metadata: Unexpected FileNotFoundError".

Suggested fix: when the snapshot directory is missing, return `declared_python: null` with
a note that the source is not on this machine. `GET /symbols/{id}` already handles the same
case with a warning instead of an error. Add a test for the missing-snapshot case.

## 2. Chess can't be migrated from 2.7 to 3.14 yet

Chess is the Python 2.7 input and Python 3.14 is the goal. The UI can upload chess and show
its graph, source and declared Python 2.7. It can't plan or run the migration:

| Blocker | Where | Owner |
|---|---|---|
| The only supported target is `modern_python3`, "legacy-style Python 3 to modern typed Python 3". `python2_to_3` returns 422 `UNSUPPORTED_TARGET`. | [targets.py](../backend/app/api/targets.py) | Dev 2 |
| The runner image is Python 3.12. The baseline needs 2.7 and the candidate needs 3.14. | sandbox image | Dev 4 |
| ZIP uploads are static-only and chess isn't in the trusted fixture allowlist, so `POST /plans` returns 409 `REPOSITORY_NOT_EXECUTABLE`. | [plans.py:55](../backend/app/orchestration/plans.py) | Dev 2, Dev 3 |
| There are no chess cases or oracle routing. Case collection still points at the orders cases. | verifier | Dev 4 |

These match items 2, 4 and 5 in [chess-demo.md](chess-demo.md).

What the frontend needs once these are fixed:

- A target that `GET /migration-targets` marks `supported: true` for chess. The Plan screen
  lists the targets and disables unsupported ones with their reason.
- The target Python version from the API. Your explorer had "Python 3.14" written into the
  page. A field such as `target_python: "3.14"` on the target would let the Plan screen show
  "Python 2.7 (declared) → Python 3.14 (target)" without hardcoding it.
- `executable: true` on the chess repository record.

## 3. Your explorer is now part of screens 01–04

`/explorer`, `RepositoryExplorer.tsx` and `App.css` are deleted. Their features moved here:

| Explorer feature | Now in |
|---|---|
| ZIP upload | 01 New migration (`/`), now "Upload a folder" |
| Declared Python version | 02 Overview, Python version panel |
| Dependency graph | 03 Graph tab |
| Module source | 04 Module inspector: select a module on the graph, then expand the panel |
| "Create upgrade plan" and "Python 3.14 (desired)" | The Plan screen, in Dev 5's next step |

To try chess: on `/`, choose "Upload a folder" and pick `demo/chess`.

If you have local edits to `RepositoryExplorer.tsx`, pulling main gives a modify/delete
conflict. Move the change into the screen that now owns it, or send it to Dev 5.

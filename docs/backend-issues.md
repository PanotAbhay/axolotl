# Notes from Dev 5: backend issues found from the frontend

Items 1–3 (23 Oct 2026) came up while folding Dev 1's explorer into the main screens. Items 4–8
(24 Oct 2026) came up while building the Plan and Run screens against Atlas Local, and items 9–13
(24 Oct 2026) while building the run timeline and checking the endpoints the Diff and Report screens
need. Item 1 is fixed on main (`edd19ea`); nothing else here is fixed in the backend yet. Where the
frontend works around an issue, the item says so.

| # | Issue | Owner | Blocks the demo? |
|---|---|---|---|
| 1 | The runtime endpoint returns 500 on other machines | Dev 1 | Fixed in `edd19ea` |
| 2 | Chess can't be migrated from 2.7 to 3.14 yet | Dev 2, Dev 3, Dev 4 | The chess demo |
| 3 | The explorer is now part of screens 01–04 | Dev 1 | No |
| 4 | Units with no visible cases can never pass | Dev 4 | Yes: `legacy_orders` ends at 2 of 6 units |
| 5 | Risk ignores the visible case counts | Dev 2 | No, but the plan shows the wrong risk |
| 6 | A run turns terminal before its last event | Dev 2 | No, the frontend works around it |
| 7 | Interrupted runs keep their running unit states | Dev 2 | No |
| 8 | Questions | Dev 2 | No |
| 9 | Importing chess takes minutes because of search indexing | Dev 1, Dev 3 | Only if chess is uploaded live |
| 10 | A unit's `attempts` reads 0 until the unit ends | Dev 2 | No, the frontend works around it |
| 11 | The diff has no baseline, so every file reads as new | Dev 4 | Yes: the diff at 2:35 in the demo, and the report's changed files |
| 12 | The unit endpoint returns no verifications | Dev 2 | The Diff screen's per-case table |
| 13 | Nothing fills the report's runtime timings | Dev 4, Dev 2 | No, the Report hides the runtime panel |

## 1. The runtime endpoint returns 500 for repos imported on another machine

Fixed by Dev 1 in `edd19ea`: a missing snapshot now returns a note instead of a 500.

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

Since 24 Oct chess is the MVP demo, with `legacy_orders` as the backup, so this is now
top priority. Tracked in [#30](https://github.com/Prittstick22/axolotl/issues/30) and its sub-tickets.

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
| ZIP upload | 01 New migration (`/`), "Upload a folder", using your folder import |
| Declared Python version | 02 Overview, Python version panel |
| Dependency graph | 03 Graph tab |
| Module source | 04 Module inspector: select a module on the graph, then expand the panel |
| "Create upgrade plan" and "Python 3.14 (desired)" | The Plan screen, in Dev 5's next step |

To try chess: on `/`, pick "Upload a folder" and choose `demo/chess`.

If you have local edits to `RepositoryExplorer.tsx`, pulling main gives a modify/delete
conflict. Move the change into the screen that now owns it, or send it to Dev 5.

## 4. Units with no visible cases can never pass (Dev 4)

This blocks the `legacy_orders` demo. `_comparison_gate` in
[verification/\_\_init\_\_.py:421](../backend/app/verification/__init__.py) marks the differential gate
as required even when the unit has no cases:
`required=name != "impacted_tests" or bool(comparisons)`. A gate with no cases reports
`skipped`, and line 500 passes a verification only when every required gate is `passed`. So a
unit with 0 visible cases fails every attempt, whatever the patch.

In run `run_bb0da2e79534` (events 76–91), `storage.py` passed the compile, impacted-tests,
existing-tests and sandbox-policy gates. It still got `verification_failed`, then `unit_blocked`
with "no verification passed within the attempt budget". Its dependants `orders.py`, `refunds.py`
and `main.py` were then skipped. The run ended "completed with warnings" at 2 of 6 units.
`main.py` also has 0 visible cases, so it would be blocked the same way.

The plan says the opposite. [plans.py:186](../backend/app/orchestration/plans.py) tells the user
that units with no visible cases are "checked only by the compile and existing-test gates, not by
differential comparison".

Suggested fix: `required=bool(comparisons)` for both comparison gates, so a gate with nothing to
compare can't fail the unit. Add a test with a unit that has no cases.

## 5. Risk ignores the visible case counts (Dev 2)

[plans.py:65](../backend/app/orchestration/plans.py) calls `build_units` without
`visible_case_counts`, so `score_risk` sees 0 cases for every unit. Every unit gets the
`no_visible_cases` factor and its risk weight. `_apply_visible_case_counts` sets
`visible_case_count` afterwards, but it doesn't recompute `risk` or `risk_factors`.

The Plan screen and the module inspector show these values as they are. `pricing.py` shows risk
"High" with the factor `no_visible_cases`, next to "Visible cases 8". Every risk label in the plan
table is higher than it should be.

Suggested fix: score each unit again with `score_risk` after the counts are applied. Add a test
that a unit with cases has no `no_visible_cases` factor.

## 6. A run turns terminal before its last event (Dev 2)

In [worker.py](../backend/app/orchestration/worker.py), every way a run ends sets the terminal
state first and records one more event after it:

| Ending | Order in the worker |
|---|---|
| Completed | `_transition(run, verdict)`, then `_generate_report` appends `report_generated`. This was 19 s later in `run_bb0da2e79534`. |
| Failed | `_fail` transitions, then appends `error` with code `RUN_FAILED`. |
| Cancelled | `_is_cancelled` transitions, then appends `error` with code `RUN_CANCELLED`. |

Spec §9.3 says the UI polls only while the run is non-terminal. A client that does exactly that
stops before `report_generated` and never sees it. For those seconds, the report endpoint also has
no report for a run that already reads as finished.

The frontend works around it. After a run ends, the event log keeps polling until it sees
`report_generated` or `error`, for at most 2 minutes. Please do one of these:

- Record the closing event before the terminal transition.
- Write the rule into SHARED_CONTRACTS §7: "a terminal run always ends with `report_generated` or
  `error`". Then every screen can rely on it.

## 7. Interrupted runs keep their running unit states (Dev 2)

When the backend restarts during a run, `mark_interrupted_runs` in
[store.py:132](../backend/app/orchestration/store.py) sets the run to `failed` with "interrupted by
server restart". The units keep `migrating` and `queued`, `current_unit` keeps its value, and no
event is recorded. The Run screen then shows a failed run whose graph still has `customers.py` as
"Migrating", and its event log just stops.

Suggested fix: do what cancellation does. Move each unfinished unit to `skipped` with a
`unit_blocked` event, and append an `error` event with a code such as `RUN_INTERRUPTED`.

## 8. Questions (Dev 2)

- **One plan can have several active runs.** `start_run` doesn't check for an active run of the
  same plan, so two clicks start two runs, each with its own Argon session. The Plan screen now
  shows "View run" when the URL already has a run, but the API still allows a second one. Should
  a second active run on the same repository get a 409?
- **Skipped units get `unit_blocked` events.** When `storage.py` is blocked, `orders.py`,
  `refunds.py` and `main.py` move to `skipped`, but each one also gets a `unit_blocked` event. The
  Run screen shows `unit_blocked` as a red failure row, so one real block shows as four red rows.
  Is this intended? A separate `unit_skipped` event type would let the UI show skips in grey
  without matching on the reason text.
- **The attempt budget isn't in the API.** The template's run header shows "Attempt 2 of 3".
  `max_patch_attempts` is only in config, so the header can show "2" but not "of 3". Could
  `RunSummary` or the plan carry it?
- **The unsupported targets' reasons are too long.** On the Plan screen at 1280×720, the four
  disabled targets take two to four lines each and push the column below the fold. Could each
  `unsupported_reason` in [targets.py](../backend/app/api/targets.py) be one short line, such as
  "Not in the MVP: needs a Python 2 runtime in the sandbox."?
- **A run cancelled before final verification gets no report.** Is that intended? If yes, the
  Report screen will say there is no report for the run, instead of waiting for one.

## 9. Importing chess takes minutes because of search indexing (Dev 1, Dev 3)

`POST /repositories/import` responds only after search indexing has finished:
[ingestion/\_\_init\_\_.py:216](../backend/app/ingestion/__init__.py) awaits `index_repository`,
which has Argon describe every chunk and then embeds them. On 24 Oct, uploading the `demo/chess`
folder (16 files, 122 chunks) through the UI held the request for more than 2 minutes. The import
then completed correctly (`folder_upload`, 15 modules, 122 chunks described and embedded).

The frontend has no request timeout, so the screen just shows "Importing…" until it finishes. In a
3-minute demo that is too long to wait on stage.

Suggested fix: save the repository and respond first, then index in the background, and show
indexing progress in `GET /system/status` or on the repository record. A cheaper option is to
skip the Argon descriptions at import time and add them when `POST /repositories/{id}/index` is
called.

## 10. A unit's `attempts` reads 0 until the unit ends (Dev 2)

`RunSummary.units[].attempts` is written only after the unit's Argon session ends
([worker.py:298](../backend/app/orchestration/worker.py)). The status is written through as it
changes, so while a unit runs the summary says `repairing` with `attempts: 0`. In run
`run_eb826f4da0d5` (24 Oct), `storage.py` failed its first verification at event 81 and repaired
for a minute with `attempts: 0`, so the Run screen's header and graph said "Attempt 1".

The frontend works around it: while a unit runs, it takes the highest `attempt` from the unit's
events, and counts a repair as the next attempt. Suggested fix: set `state.attempts` from
`controller.attempts_used` in `write_status` as well, so the summary is right during the run.

## 11. The diff has no baseline, so every file reads as new (Dev 4)

`diff()` in [workspaces.py:193](../backend/app/sandbox/workspaces.py) reads the old side from
`WORKSPACE_ROOT/runs/{run_id}/rev_baseline/`, which is never created. A run's folder holds only its
own revisions (for `run_bb0da2e79534`: `rev_9db26cbee19c`, `rev_a55b1d7b0168`, `rev_ba0dac6be1b7`,
`rev_9609090a4a3c`). Every old file reads as empty, so:

- `GET /runs/run_bb0da2e79534/diff?unit_id=unit_pricing` returns `old_content: ""` and a unified
  diff of `@@ -0,0 +1,113 @@`. The Diff screen would show all 113 lines of `pricing.py` as added.
- The report's `changed_files` lists all 9 files in the tree, including `README.md`,
  `tests/cases.json` and `tests/test_baseline.py`, though only `customers.py` and `pricing.py`
  were migrated. [builder.py:193](../backend/app/reports/builder.py) (Dev 2) uses the same diff.

The function's docstring says the baseline is "located through the run's own first revision
directory when present", but the code doesn't do that. Suggested fix: resolve `rev_baseline` to the
run's starting tree (the repository snapshot in `WORKSPACE_ROOT/snapshots/{repo_id}`, or the first
revision directory), and add a test that an unchanged file is not in the diff.

Until then, the Diff screen can take the old side from the module source endpoint.

## 12. The unit endpoint returns no verifications (Dev 2)

`GET /runs/{run_id}/units/{unit_id}` always returns `"verifications": []`
([plans_runs.py:119](../backend/app/api/plans_runs.py)), with the comment "Dev 4 owns
verification_results; read when it lands". It has landed: `list_verifications` is in
[verification/store.py:81](../backend/app/verification/store.py). For `unit_pricing` in
`run_bb0da2e79534` the endpoint returns no verifications, though `ver_dd3750652173` passed.

The Diff screen needs them for the gate table, the attempt history and the per-case old and new
outputs. The frontend can rebuild gates and attempts from the events, but the per-case comparisons
are only in the verification results. Suggested fix: return `list_verifications(run_id, unit_id)`
there, with held-out values redacted the same way as the counterexamples.

## 13. Nothing fills the report's runtime timings (Dev 4, Dev 2)

`RunReport.performance` (SHARED_CONTRACTS, `PerformanceSummary` and `UnitTiming`) is always
`null`: nothing in the backend times cases or sets the field. The Report screen was going to show a
before/after runtime comparison per unit.

Question: will the verifier time each case on the old and new code (Dev 4), and the report builder
fill `performance` (Dev 2)? If not, the Report leaves the runtime panel out instead of showing
"not measured" for every unit.

# Axolotl at Encode London 2026

Axolotl migrates a legacy Python project module by module, in dependency order. Argon,
our Gemini agent, proposes each change. An independent verifier then runs the original
and the migrated code on the same recorded behaviour cases in a restricted container
and compares their outputs. Only the verifier can mark a unit passed.

"Behaviour preserved" means agreement on the tested cases. It is never a proof of
equivalence, and every report says so.

The demo is Will's terminal chess game, migrated from Python 2.7 to Python 3.14.

This page maps each hackathon track Axolotl is entered for to what the product does,
with a link to the code, test or document behind each claim, and says plainly what has
not been demonstrated yet.

## The tracks

The track wording here is the team's record of the official brief, in
[Spec §0, §8.5 and §14](planning/Axolotl_Product_Requirements_and_Implementation_Handoff.md).
Where it differs from the
[official programme page](https://www.encodeclub.com/programmes/encode-london-2026),
the programme page is right. Whether one project can be entered for all three tracks
was an open question for the organisers in
[Spec §16](planning/Axolotl_Product_Requirements_and_Implementation_Handoff.md#16-implementation-agent-exact-starting-order).

| Track | What it asks for | Axolotl's answer | To submit |
|---|---|---|---|
| **Google DeepMind: Gemini 4 Argon, Pathway 1, *Autonomous Agents That Ship*** (primary) | A real, named user's problem, an autonomous agent that uses tools, and a concrete pass/fail verification loop | Will's chess game is the problem. Argon plans and patches through ten tools. A differential verifier in a sandbox decides pass or fail | 3-minute live demo, 2-minute Q&A, repository, 3-minute video |
| **MongoDB Atlas: *Build Anything, Change Everything*** | Atlas as the foundational datastore, using at least one of Atlas Search, Vector Search, Hybrid Search, Automated Embedding, Stream Processing or Voyage AI | Atlas is the only store. Atlas Search, Vector Search and native `$rankFusion` hybrid search all serve real queries | 3-minute video |
| **Encode: *Agents That Ship*** | End-to-end delivery, real tools, recovery from failure, usefulness, approval and permissions | A person approves the plan before anything runs. The agent's tools and limits are enforced outside the model, and a failed check drives a repair. The output is a patch, a report and the evidence behind them | 2 to 4-minute demo, README, a note on tools and approvals |

The Saint.AI WhatsApp notifications in
[#43](https://github.com/Prittstick22/axolotl/issues/43) are an unbuilt spike and are
not part of any entry.

## What a judge sees

1. **Import.** The `demo/chess` folder is uploaded. It is recognised as the trusted
   chess fixture by an exact content match, and only a trusted fixture is ever executed
   ([`trust.py`](../backend/app/ingestion/trust.py)).
2. **Graph.** Python's `ast` reads the source without importing or running it. Modules,
   symbols and import edges go into Atlas and come back as the dependency graph.
3. **Plan.** Argon proposes a migration plan in dependency order. Code checks the order,
   and a person approves the plan before a run can start.
4. **Baseline.** The original code runs on Python 2.7 in a container, and its outputs
   are recorded.
5. **Patch.** For each unit, Argon reads the source, searches the repository, looks at
   the visible cases and proposes full-file changes.
6. **Verify.** The candidate runs on Python 3.14 against 12 visible and 12 held-out
   chess cases. The unit gates are compile, differential, impacted tests, existing
   tests and sandbox policy, and a unit advances only when its required gates pass.
7. **Repair.** A failed gate hands Argon counterexamples, and it can try again within a
   fixed budget.
8. **Report.** A final integration check runs on the accepted tree. The report, patch
   and evidence download from the Report screen, with their caveats.

The timed version is [demo-script.md](demo-script.md), and Will's introduction is
[presentation.md](presentation.md).

## Google DeepMind: Gemini 4 Argon, Pathway 1

| The brief asks for | How Axolotl meets it | Evidence | Status |
|---|---|---|---|
| A real, named user's problem | Will has a terminal chess game with Python 2 packaging and wants it on Python 3.14 without breaking the moves. It is his own code, used with his permission | [README, "Fixture provenance"](../README.md#fixture-provenance), [chess-demo.md](chess-demo.md) | Real user and source. Permission to publish is still to be confirmed with Will ([#8](https://github.com/Prittstick22/axolotl/issues/8)) |
| An autonomous agent that uses tools | Argon runs on the Gemini Interactions API and chains interaction IDs from turn to turn. It has ten declared tools: repository overview, dependency graph, module source, symbol lookup, repository search, visible cases, propose patch, run verification, counterexamples and finish | [argon-agent.md](argon-agent.md), [`backend/app/agents/`](../backend/app/agents/) | Built. A live `gemini-4-argon` call requested a tool, took its result and continued, on 23 Oct |
| A concrete pass/fail verification loop | Only a persisted `VerificationResult` can mark a unit passed, and the agent's own report of success is advisory. An inconclusive gate never counts as a pass | [README, "Architecture"](../README.md#architecture), [`backend/app/verification/`](../backend/app/verification/), [`contracts.py`](../backend/app/models/contracts.py) | Built. Argon's patches for `customers.py` and `pricing.py` passed it on the `legacy_orders` test fixture in `run_bb0da2e79534` |
| A 3-minute live demo and 2-minute Q&A | A timed, click-by-click script with preflight checks and a labelled fallback recording, plus a 1:00 to 1:30 introduction and prepared Q&A answers | [demo-script.md](demo-script.md), [presentation.md](presentation.md) | Scripts ready. Rehearsals pending ([#14](https://github.com/Prittstick22/axolotl/issues/14)) |
| The repository and a 3-minute video | This repository, and a shot list for the Gemini video | [submission-videos.md](submission-videos.md) | Not recorded yet ([#15](https://github.com/Prittstick22/axolotl/issues/15)) |

### Against the judging criteria

| Criterion | Weight | What we show |
|---|---|---|
| Working live demo | 50% | A fresh run started in front of the judges on the real stack, with a real plan approval, Argon's actual tool calls, real containers and real gate results. Nothing a judge sees is mocked or driven by a timer ([SHARED_CONTRACTS, rule 2](planning/SHARED_CONTRACTS.md)) |
| Usefulness | 25% | People avoid touching legacy code because they cannot tell whether a rewrite still behaves the same. Axolotl gives a reviewer something to check: old and new outputs per case, the gate results, the diff and the limits of what was tested |
| Originality and need for Argon | 15% | Argon works across a whole repository through tools and over many turns. It plans in dependency order, patches, reads the verifier's counterexamples and repairs, with its thinking level raised from `medium` to `high` for repair diagnosis. What is new is the combination: the dependency graph controls the migration order, and the behavioural evidence is stored alongside it. We do not claim that any single part is unprecedented |
| Pitch clarity | 10% | Will's 183-word talk track with timed cues, and short answers to the questions judges are likely to ask ([presentation.md](presentation.md)) |

## MongoDB Atlas: Build Anything, Change Everything

| The brief asks for | How Axolotl meets it | Evidence |
|---|---|---|
| Atlas as the foundational datastore | Atlas (M10, MongoDB 8.0) holds everything Axolotl knows, in 13 collections: snapshot metadata, symbols, import edges, code chunks, plans, runs, the event journal, behaviour cases, verification results and counterexamples among them. There is no in-memory fallback. Without Atlas, the graph, search and run history answer `503 DATABASE_UNAVAILABLE` | [README, "MongoDB Atlas: the system of record"](../README.md#mongodb-atlas-the-system-of-record), [`indexes.py`](../backend/app/persistence/indexes.py), [`test_atlas_disabled.py`](../backend/tests/integration/test_atlas_disabled.py) |
| Atlas Search | `code_chunks_text` uses a custom analyser that splits identifiers, so `finalise` finds `finalise_amount`. It also finds code by the error string it raises | [`test_keyword_live.py`](../backend/tests/integration/test_keyword_live.py) |
| Vector Search | `code_chunks_vector` holds `gemini-embedding-001` embeddings at 768 dimensions, filtered by repository, and finds code by meaning when the name shares no words with the question | [`test_search_live.py`](../backend/tests/integration/test_search_live.py) |
| Hybrid Search | Native `$rankFusion` combines the two. Each response says whether native fusion actually ran (`native_hybrid`). If it fails, the app falls back to reciprocal rank fusion in Python and reports `false` | [`backend/app/search/`](../backend/app/search/), [`test_search_fusion.py`](../backend/tests/unit/test_search_fusion.py) |

Atlas also does work beyond search:

- Every index, regular and search, is created from code at startup and is safe to
  re-run.
- While a search index builds, search answers `503 SEARCH_INDEX_NOT_READY`. An empty
  result would look like "no matches".
- The run journal takes its sequence numbers from an atomic `$inc`, backed by a unique
  `(run_id, sequence)` index. In a live test, 50 concurrent writers got 50 distinct
  numbers.
- The Search screen shows each hit's keyword and vector rank where Atlas reports them,
  and leads from the hit to its module on the graph.

We do not use Automated Embedding, Voyage AI or Stream Processing. Embeddings come from
Gemini's `gemini-embedding-001`. The Spec lists Automated Embedding and Voyage AI as
optional extras, to add only if provisioned, and calls Stream Processing unnecessary for
the migration workflow
([Spec §8.5](planning/Axolotl_Product_Requirements_and_Implementation_Handoff.md#85-required-atlas-sponsor-feature-use)).

Every MongoDB claim, with the test that proves it and who verified it, is in the table in
[mongodb-bounty.md §2](mongodb-bounty.md#2-evidence-claim--proof). Its search rankings
come from the `legacy_orders` test fixture. Chess rankings will be whatever the
recording shows. The 3-minute video script is in
[submission-videos.md](submission-videos.md#mongodb-300).

## Encode: Agents That Ship

| The brief asks for | How Axolotl meets it | Evidence |
|---|---|---|
| End-to-end delivery | One chain from import to report: graph, approved plan, baseline, patch, verification, repair, gates, final integration and downloadable artefacts (`final_tree.zip`, a patch, `report.json`) | [architecture.md](architecture.md), [README, "Current state"](../README.md#current-state) |
| Real tools | The agent calls the repository, graph and search services and the verification controller. The verifier runs real code in Docker with `--network none`, a read-only filesystem, a non-root user, all capabilities dropped and memory, CPU and process limits | [`runner.py`](../backend/app/sandbox/runner.py), [runner/policy.md](../runner/policy.md) |
| Recovery | A failed gate gives the agent counterexamples to repair from, within a fixed attempt budget. A Gemini rate limit waits for the delay the API asks for, up to 90 seconds, and a dropped connection is retried once. A unit that still cannot pass is shown as blocked, and the units that depend on it are skipped | [argon-agent.md](argon-agent.md), [BUILD_LOG, #47](../BUILD_LOG.md) |
| Usefulness | See the DeepMind usefulness row above | |
| Approval and permissions | A person approves the plan before a run starts. Only an exact match of a trusted fixture is executed, and any other upload is analysed statically. A per-unit file allowlist and a patch budget are enforced in code, outside the model. Held-out cases are never shown to the model and are redacted from every read path. Repository text is treated as untrusted data, and the `legacy_orders` test fixture contains a prompt-injection docstring to test that | [`trust.py`](../backend/app/ingestion/trust.py), [argon-agent.md, "Tools and boundaries"](argon-agent.md#tools-and-boundaries), [`test_prompt_injection.py`](../backend/tests/security/test_prompt_injection.py) |

The track also asks for a note on the tools used to build Axolotl and how changes were
approved. A draft is in
[submission-videos.md](submission-videos.md#agents-that-ship-300-allowed-window-in-15-24-minutes);
the team still has to confirm it names the coding tools actually used.

## What is demonstrated and what is pending

Update this table when any of these issues closes.

| Item | State |
|---|---|
| The full chain on the `legacy_orders` test fixture | Done. In `run_bb0da2e79534`, Argon's patches for `customers.py` and `pricing.py` passed independent verification |
| Chess pieces: Python 2.7 and 3.14 sandbox images, 24 behaviour cases, the `python2_to_3` target | Merged ([#22](https://github.com/Prittstick22/axolotl/issues/22), [#23](https://github.com/Prittstick22/axolotl/issues/23), [PR #76](https://github.com/Prittstick22/axolotl/pull/76)) |
| A chess run that reaches a verdict | **Not yet.** No chess run has gone end to end ([#4](https://github.com/Prittstick22/axolotl/issues/4), [#7](https://github.com/Prittstick22/axolotl/issues/7)) |
| Rehearsals of the introduction and demo | Pending ([rehearsal-log.md](rehearsal-log.md)) |
| The three submission videos and their checked links | Pending ([#15](https://github.com/Prittstick22/axolotl/issues/15)) |
| DeepMind write-up from the final live run | Pending ([#13](https://github.com/Prittstick22/axolotl/issues/13)) |
| MongoDB write-up and Atlas demo rehearsal | Draft in [mongodb-bounty.md](mongodb-bounty.md) ([#12](https://github.com/Prittstick22/axolotl/issues/12)) |

Test counts and the per-area build state are in
[README, "Current state"](../README.md#current-state).

## Limits

- Agreement on recorded cases is not equivalence. Behaviour the cases do not cover can
  change without anyone noticing, and the report says so.
- The Docker sandbox is a restricted container. It is not a hardened multi-tenant
  isolation service, which is why only trusted fixtures run
  ([runner/policy.md](../runner/policy.md)).
- The graph shows imports only. Call and inheritance edges are not extracted yet.
- Semantic and hybrid search need a Gemini key with quota. Without one, keyword search
  still works and every response says it ran keyword-only.
- Snapshots are local to the machine that imported them, so whoever imports the demo
  repository has to run the demo.

The full list is under "Coverage caveats" and "Known issues and failures" in the
[README](../README.md#coverage-caveats).

## Where to look

- [README](../README.md): setup, architecture, models and settings
- [architecture.md](architecture.md): the state machine and where each safety rule is enforced
- [argon-agent.md](argon-agent.md): the agent, its tools and its boundaries
- [mongodb-atlas.md](mongodb-atlas.md) and [mongodb-bounty.md](mongodb-bounty.md): collections, indexes and the Atlas evidence
- [chess-demo.md](chess-demo.md): the chess fixture and its behaviour cases
- [demo-script.md](demo-script.md), [presentation.md](presentation.md) and [submission-videos.md](submission-videos.md): the demo, the pitch and the videos

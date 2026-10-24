# The three-minute walkthrough

A chronological tour of the whole application, built around one live chess migration.
Supersedes the timed table in [demo-script.md](demo-script.md), which predates the
Search, Ask, Changes, Dependencies and Docs screens. That document's **preflight
checklist and fallbacks still apply** and are not repeated here.

## The idea that makes it fit

A run takes about 1 minute 44 seconds. The demo is 180 seconds. So the run cannot be
watched — but it should not be hidden either.

**Start the run at 1:00, then tour the rest of the application while it works.** The
migration is genuinely running in the background the whole time the judges are looking
at search, the chat and the docs. Nothing is dead time, nothing is faked, and the run
is finished when we come back to it at 1:55.

Five speakers. The breaks below fall naturally at 0:15, 1:00, 1:40, 2:10 and 2:35 —
divide them however suits the team.

## Intro (0:00–0:15)

> "Every team has code nobody dares touch. Not because it is bad, but because nobody
> can prove a rewrite still behaves the same way.
>
> This is Will's chess game. It is real, it is his, and it is stuck on Python 2.7.
> Axolotl will migrate it to 3.14 — and an independent verifier, not the AI, decides
> whether each change is safe."

## Walkthrough (0:15–2:50)

| Time | Click / show | Say | Why it earns the time |
|---|---|---|---|
| 0:15–0:30 | **New migration.** Chess is already selected as a built-in fixture. Point at the upload option beside it | "Chess ships with the project, so it runs on any laptop. Anything you upload instead is read, never executed — only an exact content match of a trusted fixture is allowed to run." | **Encode: permissions.** The trust gate is the first thing a judge sees, before anything runs |
| 0:30–0:42 | **Graph.** Click one module, follow an import edge | "Python's own parser reads the source without importing or running it. These edges are facts from the code, and they decide the migration order." | **Novel.** The dependency graph is not decoration — it controls the order of work |
| 0:42–1:00 | **Plan.** Scroll the dependency order, then **Approve**, then **Start migration** | "Argon proposed this order; code checks it is dependency-first. Nothing runs until a person approves it. I'm approving it now." | **Encode: human approval.** A real gate, enforced outside the model. **The run starts here and keeps running** |
| 1:00–1:20 | **Search.** Query `get the final amount` in **keyword**, then switch to **hybrid** | "Keyword search returns the wrong function — 'get' matches `get_order`. Hybrid finds the right one, and the badge says `native_hybrid`, so that is Atlas's own `$rankFusion`, not something we faked in Python." | **MongoDB bounty, the strongest 20 seconds we have.** Atlas Search, Vector Search and native hybrid fusion, with the difference visible on screen |
| 1:20–1:40 | **Ask pane**, same screen. Ask "where is castling decided?" | "Same hybrid search, now as retrieval for Gemini. Every answer cites `path:line` from code it actually read, and underneath you can see the retrieval — which tools ran, which engine answered. If it finds nothing it says so rather than inventing." | **Both bounties at once.** Gemini tool use over Atlas hybrid search, with the evidence shown, not asserted |
| 1:40–1:55 | **Docs**, then **Dependencies** | "Documentation generated for the legacy and the migrated code side by side. And the dependency changes the migration introduced — including packages with known vulnerabilities." | Breadth. Two screens, one sentence each; do not linger |
| 1:55–2:10 | **Run.** Point at the live event journal, tool calls, per-unit status | "This has been running since I approved it. Every model turn, tool call and verdict is journalled in Atlas as it happens. A patch is a proposal until the checks pass." | **DeepMind: an agent that uses tools.** Real tool calls, timestamped, not narrated |
| 2:10–2:35 | **Click a unit → Verification.** Show visible cases passing, the held-out case failing, the counterexample, then the repair | "Here is the whole point. The visible tests pass. A held-out case the model has never seen does not — and that is what blocks it. The agent gets the counterexample, not the hidden inputs, and tries again." | **The thesis, and the single most important 25 seconds.** This is what "independently verified" means |
| 2:35–2:50 | **Report.** Verdict, migration summary, security section, the NOT-A-PROOF line, then **Download migrated codebase** | "The verdict, what changed, and the honest caveat: this is agreement on tested cases, never proof of equivalence. And the migrated project downloads here." | **Encode: end-to-end delivery.** It ends in something you can actually take away |

## Outro (2:50–3:00)

> "Nothing you just saw was mocked. Real containers, real model calls, real cases.
>
> Axolotl never claims your code is equivalent. It claims agreement on the cases it
> tested, and it shows you every case, gate and counterexample behind that claim.
>
> That is the difference between trusting an AI with your legacy code, and being able
> to check it."

## What has to be true before the clock starts

- **Docker running, all five images built** (`README`, Quick start). Both the live run
  and the replay need them: the replay substitutes the model, not the verifier, so the
  gates run for real either way.
- **Chess imported in advance on the shared cluster.** Import and indexing take minutes
  and belong outside the three.
- **A Gemini key with quota.** One run is roughly 48 embedding calls against a
  1000-a-day free tier. Check before presenting, not during.
- **Tabs pre-opened** in walkthrough order, so no time goes on navigation.
- Rehearse the 1:00 hand-off. If the run has not started by 1:05, the second half has
  nothing to come back to.

## If something goes wrong

**The live run finds no regression.** Likely, and it is the one moment the demo cannot
do without. Switch to the deliberately broken promotion candidate already in the
repository (`backend/tests/integration/test_chess_cases_docker.py -k promotion`): the
visible cases still pass and the held-out underpromotion case fails. Keep the label
**"separate verifier check — deliberately injected bug"** on screen, and never imply the
model produced it.

**The run stalls or is not finished at 1:55.** Say what it is actually doing, then show
the recorded run `run_70e126c3acf2` with its date and run id visible. It completed
across all 14 units. Do not replay seeded events as live.

**Search or the Ask pane has no quota.** Both fall back to keyword and say so on screen
(`mode_used: "keyword"`). Say it out loud rather than hiding it — "that is the fallback
working" is a better answer than a blank panel.

**The demo branch is 28 commits behind main** and does not have the Search, Ask,
Dependencies or Docs screens. If the demo runs from `demo/argon-replay`, this
walkthrough loses four of its stops. Decide which matters more, in advance, not live.

## What we do not claim

Say these only if asked, but have them ready:

- Agreement on recorded cases is not equivalence. Untested behaviour can change.
- The sandbox is a restricted container, not hardened multi-tenant isolation. That is
  why only trusted fixtures execute.
- The graph shows imports. Call and inheritance edges are not extracted.
- Snapshots are local to the machine that imported them.

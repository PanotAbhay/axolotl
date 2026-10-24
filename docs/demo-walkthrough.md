# The three-minute walkthrough

A chronological tour of the whole application, built around one live chess migration.
Supersedes the timed table in [demo-script.md](demo-script.md), which predates the
Search, Ask, Changes, Dependencies and Docs screens. That document's **preflight
checklist and fallbacks still apply** and are not repeated here.

**The words live in [demo-transcript.md](demo-transcript.md) and only there.** This file
carries the clicks, the reasoning and the fallbacks; the *Words* column names the
section to say. Two copies of a script drift, and the first thing to go stale is the
one nobody rehearses from.

**No personal names in the spoken script.**

## The idea that makes it fit

A run takes about 1 minute 44 seconds. The demo is 180 seconds. So the run cannot be
watched — but it should not be hidden either.

**Start the run at 1:00, then tour the rest of the application while it works.** The
migration is genuinely running in the background the whole time the judges are looking
at search, the chat and the docs. Nothing is dead time, nothing is faked, and the run
is finished when we come back to it at 1:52.

Five speakers across six blocks — see *Handing over* below for the split.

## Intro (0:00–0:22)

The words are in [demo-transcript.md](demo-transcript.md). Two paragraphs, a beat
and a half between them, and do not rush the second: it carries the whole claim.

## Walkthrough (0:22–2:42)

| Time | Click / show | Words | Why it earns the time |
|---|---|---|---|
| 0:22–0:35 | **New migration.** Chess is already selected as a built-in fixture. Point at the upload option beside it | §1 Import | **Encode: permissions.** The trust gate is the first thing a judge sees, before anything runs |
| 0:35–0:48 | **Graph.** Click one module, follow an import edge | §2 Graph | **Novel.** The dependency graph is not decoration — it controls the order of work |
| 0:48–1:00 | **Plan.** Scroll the dependency order, then **Approve**, then **Start migration** | §3 Plan and approval | **Encode: human approval**, enforced outside the model. **The run starts here and keeps running** |
| 1:00–1:20 | **Search.** Query `get the final amount` in **keyword**, then switch to **hybrid** | §4 Search | **MongoDB bounty, the strongest 20 seconds we have.** Atlas Search, Vector Search and native fusion, with the difference visible on screen |
| 1:20–1:40 | **Ask pane**, same screen. Ask "where is castling decided?" | §5 Ask | **Both bounties at once.** Gemini tool use over Atlas hybrid search, with the evidence shown rather than asserted |
| 1:40–1:52 | **Docs**, then **Dependencies** | §6 Docs and dependencies | Breadth. Two screens, one sentence each; do not linger |
| 1:52–2:08 | **Run.** Point at the live event journal, tool calls, per-unit status | §7 Run | **DeepMind: an agent that uses tools.** Real tool calls, timestamped, not narrated |
| 2:08–2:29 | **Click a unit → Verification.** Show the visible cases passing, the held-out case failing, the counterexample, then the repair | §8 Verification | **The thesis, and the most important 21 seconds.** This is what "independently verified" means |
| 2:29–2:42 | **Report.** Verdict, migration summary, security section, the NOT-A-PROOF line, then **Download migrated codebase** | §9 Report | **Encode: end-to-end delivery.** It ends in something you can actually take away |

## Outro (2:42–3:00)

The words are in [demo-transcript.md](demo-transcript.md). This is the slowest
thing in the demo. Eighteen seconds for thirty-six words is deliberate.

## Delivery

The transcript is 392 spoken words across 180 seconds: **131 words a minute**, against a
normal demo pace of 130 to 150. Every individual beat sits between 110 and 140. If one
feels rushed, the cause is a skipped pause rather than too many words.

The slackest beat is 0:48 to 1:00, at 110 — and that is correct, because it is two clicks
and waiting for the run to actually start. Do not fill that silence.

These numbers were measured from the transcript, not estimated. Re-measure if the words
change: the first draft of the intro and outro read at 252 and 354 words a minute, which
is not a tight script but an unspeakable one, and it did not look wrong on the page.

### Pauses

- **Comma: a quarter beat.** Enough for a breath, not enough to land.
- **Full stop: a full beat**, about half a second to a second.
- **Em dash: longer than a comma.** It is a pivot, so let the turn register.
- **Between paragraphs in the intro and outro: a second and a half.** Those two are
  the only places in the demo where silence is doing work.
- Never breathe mid-phrase for air. The sentences are short enough that you will not
  run out; if you do, you are going too fast.

### Clicking and speaking

This is where demos are usually lost.

- **Click first, then speak.** Eyes follow the cursor, and for about half a second
  after a click nobody is listening. A sentence spoken over your own click is a
  sentence nobody heard.
- **Let the screen land before the sentence that explains it.** The explanation should
  arrive to a picture that is already there.
- **Never narrate the click.** Not "now I'll click Search" — say what it means. The
  judges can see the cursor; they cannot see the reasoning.

### Emphasis

One stressed word per sentence, not three. Everything stressed is nothing stressed.

The words carrying the argument are: *independent*, *never seen*, *native*, *actually
read*, *agreement*. Those are the claims. Land them and let the rest run flat.

### Saying the technical bits

| On screen | Say |
|---|---|
| `native_hybrid` | "native hybrid" — never "underscore" |
| `$rankFusion` | "rank fusion" |
| `path:line` | "path and line" |
| `run_70e126c3acf2` | Do not say it. Point at it and say "the recorded run" |
| `12 visible, 12 held out` | "twelve visible, twelve held out" — numbers under a hundred are words |

### The one line that is fixed wording

> "agreement on the cases it tested, never proof of equivalence"

Say it exactly. This is the claim the entire project rests on, and every loose paraphrase
of it overclaims. "It proves the code is the same" is the one sentence that could lose
the room, and it is an easy thing to say by accident at speed.

### Handing over

The transcript is in six blocks: intro, then import-graph-plan, search-ask,
docs-run, verification-report, then the outro. Five speakers, so one takes both
the intro and the outro — the same voice opening and closing reads as deliberate.

Handoffs fall at 0:22, 1:00, 1:40, 1:52, 2:08 and 2:42.

- **The incoming speaker starts on the new screen**, not the outgoing one. The click is
  the handoff.
- **One beat of silence**, no overlap. Two voices at once reads as a mistake even when
  it is planned.
- **Do not announce it.** Never "and now Caroline will show you the search". Just
  continue the sentence the demo is making.

### When something goes wrong

- **Say what is actually on screen, in the present tense.** "This is still verifying" is
  fine. "It usually finishes by now" invites the question you do not want.
- **Silence beats filler.** Two seconds of a screen loading is invisible. Two seconds of
  "um, it is just loading" is not.
- Never apologise for the software mid-demo. State it, move, carry on.

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

**The run stalls or is not finished at 1:52.** Say what it is actually doing, then show
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

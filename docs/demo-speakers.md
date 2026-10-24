# Who says what

The script is [demo-transcript.md](demo-transcript.md); this is the same words, split by
speaker. Delivery rules are in [demo-walkthrough.md](demo-walkthrough.md).

Dev speaks twice — the intro and steps 8–9. Caroline approves the plan in step 3, which
is why step 7 says "we approved the plan" and not "I".

---

**Dev** — *Intro, 0:00*

Welcome to Axolotl — the safe way to migrate legacy code nobody dares touch, because
nobody can prove a rewrite behaves the same.

Today's example: a chess game stuck on Python 2.7. Axolotl migrates it to 3.14, runs
old and new on the same inputs, and compares every output.

---

**Caroline** — *Steps 1–3, 0:22*

Chess ships with the project, so every laptop gets the same repository.

Upload anything else and it's parsed, never executed — only an exact content-hash match
is allowed to run.

Python's `ast` reads the source — no import, no execution.

Modules, symbols and edges go into Atlas. That order becomes the migration order:
dependencies first, so a failure stays local.

Gemini proposed this order. Our code checks it really is dependency-first.

Nothing runs until a person approves it. I'm approving it now.

---

**Abhay** — *Steps 4–5, 1:00*

Keyword search returns the wrong function — our identifier analyser splits names, so
"get" matches "get order".

Vector search finds it by meaning instead. Atlas fuses both with rank fusion, and the
badge confirms that ran natively, inside the database.

The same hybrid search, now as retrieval for Gemini.

Five read-only tools — search, source, symbols, the graph. It cannot patch or verify
from here.

Every answer cites path and line from code it actually read. Find nothing, and it says
so rather than inventing.

---

**William** — *Steps 6–7, 1:40*

Documentation generated for the legacy and the migrated code, side by side.

And every dependency the migration changed — including the ones carrying known
vulnerabilities.

This has been running since we approved the plan.

Every model turn, every tool call, every gate result lands in an append-only journal in
Atlas as it happens.

A patch stays a proposal until the gates pass.

---

**Dev** — *Steps 8–9, 2:08*

Here is the whole point.

Twenty-four recorded cases. Twelve the model can see; twelve it never will.

The visible twelve pass. A held-out case fails — and that is what blocks it. The agent
gets the counterexample, never the hidden input. Then it tries again.

The verdict, the diff, and the caveat: agreement on the cases it tested, never proof of
equivalence.

The migrated project downloads here — code, report and evidence.

---

**Moe** — *Outro, 2:42*

Nothing you saw was mocked. Real containers, real cases.

Axolotl never claims your code is equivalent. It claims agreement on what it tested —
and hands you every case, gate and counterexample behind that claim.

That's trusting an AI, versus checking it.

---

## Share of the three minutes

| Speaker | Section | Seconds | Words |
|---|---|---|---|
| Dev | Intro | 22 | 49 |
| Caroline | Steps 1–3 | 38 | 82 |
| Abhay | Steps 4–5 | 40 | 85 |
| William | Steps 6–7 | 28 | 62 |
| Dev | Steps 8–9 | 34 | 72 |
| Moe | Outro | 18 | 42 |

Dev has 56 seconds across two turns; William has the shortest run at 28. Abhay carries
both bounty moments, search and the Ask pane, in one 40-second block — the one worth
rehearsing twice.

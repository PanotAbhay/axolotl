# Demo transcript

Spoken words only. Clicks, timings, reasoning and fallbacks are in
[demo-walkthrough.md](demo-walkthrough.md); delivery rules are in its *Delivery*
section. Section breaks are where the speakers change over; who says what is in
[demo-speakers.md](demo-speakers.md).

**No personal names in the spoken script.** Say "ours", "a teammate", "one of us".

Every section sits between 102 and 140 words a minute. Nothing here needs to be rushed,
and if a beat feels rushed, the cause is a skipped pause rather than too many words.

---

## Intro — 0:00

Welcome to Axolotl — the safe way to migrate legacy code nobody dares touch, because
nobody can prove a rewrite behaves the same.

Today's stand-in is a chess game stuck on Python 2.7. Axolotl migrates it to 3.14, runs
old and new on the same inputs, and compares every output.

---

## 1. Import — 0:22

Axolotl takes any Python project.

Point it at your own, and it's parsed, never executed — only an exact content-hash match
runs.

## 2. Graph — 0:32

Python's `ast` reads the source — no import, no execution.

Modules, symbols and edges go into Atlas — and that structure sets the migration
order. Dependencies first, so a failure stays local.

## 3. Plan and approval — 0:46

Gemini proposed this order. Our code checks that it really is dependency-first.

Nothing runs until a person approves it. I'm approving it now.

---

## 4. Search — 1:00

Keyword search returns the wrong function — our identifier analyser splits names, so
"get" matches "get order".

Vector search finds it by meaning instead. Atlas fuses both with rank fusion, and the
badge confirms it ran natively, inside the database.

## 5. Ask — 1:19

The same hybrid search, now as retrieval for Gemini.

Five read-only tools — search, source, symbols, the graph. It can't patch or verify anything
from here.

Every answer cites path and line from code it actually read. If it finds nothing, it says
so rather than inventing.

---

## 6. Docs and dependencies — 1:40

Documentation, generated for the legacy and the migrated code, side by side.

And every dependency the migration changed — including the ones carrying known
vulnerabilities.

## 7. Run — 1:52

This has been running since we approved the plan.

Every model turn, every tool call, every gate result goes into an append-only journal in
Atlas as it happens.

A patch stays a proposal until the gates pass.

---

## 8. Verification — 2:08

This is the whole point.

Twenty-four recorded cases. Twelve the model can see; twelve it never will.

The visible twelve pass. A held-out case fails — and that's what blocks it. The agent
gets the counterexample, never the hidden input. Then it tries again.

## 9. Report — 2:29

The verdict, the diff, and the caveat: agreement on the cases it tested, never proof of
equivalence.

The migrated project downloads here — code, report and evidence.

---

## Outro — 2:42

Nothing you saw was mocked. Real containers, real cases.

Axolotl never claims your code is equivalent. It claims agreement on what it tested —
and hands you every case, gate and counterexample behind that claim.

That's trusting an AI, versus checking it.

# Demo transcript

Spoken words only. Clicks, timings, reasoning and fallbacks are in
[demo-walkthrough.md](demo-walkthrough.md); delivery rules are in its *Delivery*
section. Section breaks are where the five speakers change over.

Every section sits between 94 and 135 words a minute. Nothing here needs to be rushed,
and if a beat feels rushed, the cause is a skipped pause rather than too many words.

---

## Intro — 0:00

Every team has code nobody dares touch. Not because it's bad — because nobody can prove
a rewrite still behaves the same.

Will's chess game is stuck on Python 2.7. Axolotl migrates it to 3.14, and an
independent verifier — not the AI — decides if each change is safe.

---

## 1. Import — 0:22

Chess ships with the project, so it runs on any laptop.

Anything you upload instead is read, never executed. Only an exact match of a trusted
fixture runs.

## 2. Graph — 0:34

Python's own parser reads the source, without importing it and without running it.

These edges are facts from the code — and they decide the migration order.

## 3. Plan and approval — 0:46

Argon proposed this order. Code checks that it is dependency-first.

Nothing runs until a person approves it. I am approving it now.

---

## 4. Search — 1:00

Keyword search returns the wrong function. "Get" matches "get order".

Hybrid finds the right one — and the badge says native hybrid, so that is Atlas's own
rank fusion, not something we faked in Python.

## 5. Ask — 1:20

Same hybrid search, now as retrieval for Gemini.

Every answer cites the path and line, from code it actually read. Underneath, you can
see the retrieval — which tools ran, and which engine answered.

If it finds nothing, it says so, rather than inventing.

---

## 6. Docs and dependencies — 1:40

Documentation, generated for the legacy and the migrated code, side by side.

And the dependency changes the migration introduced — including packages with known
vulnerabilities.

## 7. Run — 1:52

This has been running since I approved it.

Every model turn, every tool call, every verdict — journalled in Atlas as it happens.

A patch is only a proposal, until the checks pass.

---

## 8. Verification — 2:08

Here is the whole point.

The visible tests pass. A held-out case the model has never seen does not — and that is
what blocks it.

The agent gets the counterexample, but never the hidden inputs. Then it tries again.

## 9. Report — 2:29

The verdict. What changed. And the honest caveat: this is agreement on the cases it
tested, never proof of equivalence.

And the migrated project downloads here.

---

## Outro — 2:42

Nothing you saw was mocked. Real containers, real cases.

Axolotl never claims your code is equivalent — it claims agreement on what it tested,
and shows you the evidence.

That's trusting an AI, versus checking it.

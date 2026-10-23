# MongoDB bounty write-up (draft)

Owner: Dev 3. Source material for the README's MongoDB section (Dev 2 pastes it in) and
for the 3-minute MongoDB video (Dev 5). Every claim below points at the code or test
that proves it. **If a claim stops being true, delete it here rather than soften it.**

Technical detail lives in [`mongodb-atlas.md`](mongodb-atlas.md).

---

## 1. README section (paste-ready)

> ### MongoDB Atlas: the system of record
>
> Axolotl keeps everything it knows in MongoDB Atlas (M10, MongoDB 8.0): the
> repository snapshot metadata, every symbol and import edge of the dependency graph,
> the code chunks that search runs over, migration plans and runs, an append-only event
> journal, behaviour cases, verification results and counterexamples. There is no
> in-memory fallback. Switch Atlas off and the graph, search and run history stop with
> a clear `503 DATABASE_UNAVAILABLE`; they never quietly answer from a fake.
>
> **Atlas Search** (`code_chunks_text`) finds code by exact name or error string. A
> custom analyser splits identifiers, so `finalise_amount` and `finalise` both land on
> `pricing.finalise_amount`.
> **Atlas Vector Search** (`code_chunks_vector`, Gemini `gemini-embedding-001`, 768
> dimensions, filtered by repository) finds code by meaning: "where does the final
> customer bill get rounded?" finds `finalise_amount`, whose name shares none of those
> words.
> **Native hybrid search** fuses both with `$rankFusion`. Each result shows its keyword
> rank and vector rank, and the response says whether native fusion actually ran
> (`native_hybrid`); it is measured, never assumed.
>
> All indexes, regular and search, are created from code at startup and are safe to
> re-run. Search readiness comes from Atlas itself: while an index builds, search
> answers `503 SEARCH_INDEX_NOT_READY` instead of an empty list that would look like
> "no matches". The run journal gets its sequence numbers from an atomic `$inc`, with a
> unique `(run_id, sequence)` index as a backstop; 50 concurrent writers produce 50
> distinct numbers.

---

## 2. Evidence: claim → proof

| Claim | Proven by | Verified |
|---|---|---|
| All 12 collections and 21 regular indexes are created at startup, and a second run changes nothing | `backend/tests/integration/test_persistence_live.py` (real Atlas, throwaway database) | Dev 3, live |
| Existing indexes are never dropped or renamed; a clash is reported, not "fixed" | same file, `test_an_existing_index_is_never_modified` | Dev 3, live |
| The dependency graph lives in Atlas: the real import writes repository, symbols and edges, and the UI graph, scheduling graph (exactly the 7 T-03 edges), module inspector and symbol lookup all read them back | `tests/integration/test_graph_live.py` (real Atlas, throwaway database, 10 cases) | Dev 3, live |
| Exact-name keyword search (T-06): `finalise_amount`, `finalise`, `pricing.finalise_amount`, `discount_rate` and `place_order` each return their symbol first | `tests/integration/test_keyword_live.py` (real Atlas, no Gemini key needed) | Dev 3, live |
| Error-string search: `"quantity must not be negative"` and `"quantity is required"` find `pricing.line_gross`, the function that raises them, ahead of the test whose name shares two of the words | same file; a boosted exact-phrase match on `source` (with the boost weakened, exactly these two fail) | Dev 3, live |
| Semantic search (T-07): "where does the final customer bill get rounded?" → `pricing.finalise_amount` rank 1 in hybrid (`native_hybrid: true`; keyword alone ranks it 4th) and in vector | `tests/integration/test_search_live.py` (needs a Gemini key); API check on `axolotl` | Dev 2; Dev 3 on 23 Oct **with no chunk descriptions** (the key had no generation quota), so embeddings came from code and identifiers alone |
| The Spec §8.7 demo phrase "customer payment rounding" → `finalise_amount` rank 1 in **vector** mode, rank 2 in hybrid (a test whose name contains "customer" and "pays" ranks first) | API check on `axolotl` | Dev 3. Use vector mode, or the T-07 phrasing, in the video |
| Hybrid beats keyword alone: on the T-07 query keyword ranks the function 5th, vector 1st, fusion 1st | `test_fusion_can_beat_keyword_search_on_its_own` | Dev 2, live |
| `native_hybrid: true` only when `$rankFusion` actually ran; any failure falls back to Python reciprocal rank fusion and says `false` | `backend/app/search/__init__.py::_hybrid`, `tests/unit/test_search_fusion.py` | offline |
| Search never answers while an index is building; readiness follows Atlas's `queryable` flag | `tests/unit/test_search_safety.py`; observed on `axolotl` (`building`, then `ok`, after a definition change) | offline; observed live by Dev 3 |
| Disabling Atlas breaks the journeys with 503s, three ways (no URI, nothing listening, unknown host): graph, search and repositories, and the run/plan history | `tests/integration/test_atlas_disabled.py` (40 cases; 18 fail with the guard removed) for Dev 3's endpoints; Dev 2's fix for `/runs` and `/plans` | Dev 3; run/plan endpoints checked by Dev 3 on 23 Oct |
| The event journal is gap-free and race-free | `test_atlas_live.py::test_sequences_are_unique_under_concurrency` (50 concurrent writers) | Dev 2, live |
| Held-out test cases can never become searchable | `HeldOutLeak` in `app/search/chunking.py`; `test_search_safety.py` | offline |
| Embeddings never leave the database | `HIDDEN_FIELDS` projection in `app/search/__init__.py` | offline |

---

## 3. Video script points (3 minutes, for Dev 5)

Follows Spec §8.7. Times are targets.

1. **0:00-0:20 Status chips.** `/system/status`: MongoDB `ok`, keyword index `ok`,
   vector index `ok`. Say: "Every chip is a real call to Atlas, not a config flag."
2. **0:20-0:50 The persisted graph.** Import `legacy_orders`; the dependency graph
   renders from the `symbols` and `edges` collections. Say: "Parsed from the code with
   Python's AST, stored in Atlas. The model never invents an edge."
3. **0:50-1:40 Semantic search (the moment).** Type *"where does the final customer
   bill get rounded?"*. `pricing.finalise_amount` comes first, though its name shares
   no word with the question. Show the keyword rank / vector rank breakdown and the
   `native_hybrid: true` label. Say: "Keyword search alone ranks it fifth. Vector search
   ranks it first. Atlas's native `$rankFusion` combines them."
4. **1:40-2:00 Click through.** The hit highlights `pricing.py` in the graph, with the
   modules that depend on it.
5. **2:00-2:30 The evidence trail.** Open the counterexample and verification event for
   `pricing.py` from a migration run, both read back from Atlas. Say: "The verifier's
   evidence lives in Atlas too, so the history reloads exactly."
6. **2:30-3:00 Pull the plug.** Restart with a dead `MONGODB_URI`: chips go red, graph
   and search answer `503 DATABASE_UNAVAILABLE`. Say: "No in-memory fallback. Atlas
   isn't storage on the side; without it there is no product."

**Before recording, all of these must be true:**

- [ ] A Gemini key **with quota** on the recording machine, and
      `POST /repositories/{id}/index` run on the demo repository so chunks have
      embeddings (and descriptions, if a generation model has quota). Every search in
      vector or hybrid mode also embeds the query, one call per search: on 23 Oct the
      team key ran out of embedding quota after a few hundred calls. Do not re-index
      or run the live search tests right before recording.
- [ ] The frontend has the graph view and a search box with the rank breakdown. Today
      it shows the status chips only.
- [ ] One end-to-end migration run in the demo database, so step 5 has a
      counterexample and a verification event to open (`axolotl` has none yet).
- [ ] Indexes warmed: boot once, import, wait for both chips to read `ok`.

---

## 4. Questions judges may ask

- **Why not a graph database?** The graph is small and read whole: one query fetches a
  repository's edges into NetworkX for scheduling. Keeping it beside the symbols,
  chunks and run history in one Atlas cluster means one source of truth and one
  failure mode, rather than two stores that can disagree.
- **Is the hybrid search really native?** Yes, when `native_hybrid` is `true`: that
  flag is set only when `$rankFusion` actually executed. If it ever fails, the app
  falls back to reciprocal rank fusion in Python and says `false`. `$scoreFusion`
  needs 8.2+; this cluster is 8.0.34.
- **What happens while an index is building?** Search answers
  `503 SEARCH_INDEX_NOT_READY`. A building index returns zero results rather than an
  error, which would otherwise look like "nothing matched".
- **What if the model writes a wrong description?** Descriptions come from a real
  Gemini call and are only used to find code, never to decide anything. If generation
  fails, the field stays empty; nothing is invented. Pass/fail always comes from the
  verifier, never the model.
- **Could a malicious file instruct the model through search?** Source is framed as
  untrusted data in the description prompt, and the fixture deliberately contains a
  prompt-injection docstring (T-18) to test exactly that.

---

## 5. Honest limits (keep these in the README)

- Semantic and hybrid search need a Gemini key at import time. Without one, keyword
  search still works and every response says it ran keyword-only.
- `calls` and `inherits` edges are not extracted yet; the graph shows imports only.
- Dynamic imports via `getattr` or strings are not detected yet; only
  `importlib.import_module`, `__import__` and `reload` are.

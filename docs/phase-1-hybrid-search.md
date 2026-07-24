# Phase 1: Hybrid Search (Vector + BM25)

Mid-phase working document — not the final `docs/phase-1-rag-architecture.md`
decision doc, which comes once reranking (the last open item) is done.
Companion to [phase-1-pgvector.md](./phase-1-pgvector.md).

## What was built

- `src/retrieval/bm25_search.py` — BM25 keyword search (`rank_bm25`) over the
  same 118 structurally-chunked corpus used for pgvector.
- `src/retrieval/hybrid_search.py` — combines vector and BM25 rankings via
  **Reciprocal Rank Fusion (RRF)**: an item's fused score is
  `sum(1 / (k + rank))` across every ranked list it appears in. RRF only
  looks at rank *position*, not raw score — deliberately, since BM25 scores
  are unbounded and corpus-size dependent while cosine similarity is bounded
  to [0, 1]; a naive weighted sum of the two would need careful,
  corpus-specific normalization tuning that RRF avoids entirely.
- `src/eval/hybrid_search_eval.py` — compares vector-only, BM25-only, and
  hybrid across two different test sets, deliberately, because the golden
  set alone can't show hybrid search "winning" (vector search already hits
  100% on it — see [phase-1-pgvector.md](./phase-1-pgvector.md)).

## Test 1: the golden set (19 semantic/factual questions)

| Method | Hit rate |
|---|---|
| Vector-only | 100% (19/19) |
| BM25-only | 95% (18/19) |
| Hybrid (RRF) | 100% (19/19) |

BM25 missed one: *"What diagnosis did Sofia Ramirez receive at the emergency
room?"* — a paraphrase question with no strong literal keyword overlap with
the source text's actual wording ("distal radius fracture"). Hybrid search
correctly recovered this via RRF, since vector search alone had it right and
fusion combines both rankings rather than picking one exclusively. This is
hybrid search working as intended: BM25's one weakness got covered by vector
search's strength.

## Test 2: bare identifier lookup queries (5 queries, just a document ID as the query)

This test was specifically designed to check BM25's expected advantage —
exact string/keyword matching should be very good at literal identifier
lookup, a case dense embeddings are sometimes weaker at.

| Method | Hit rate |
|---|---|
| Vector-only | 100% (5/5) |
| BM25-only | 80% (4/5) |
| Hybrid (RRF) | 80% (4/5) |

**This is the opposite of what was predicted.** Vector search won outright,
and hybrid search actually matched BM25's *worse* result instead of
inheriting vector's better one — for the query `"MED-0603-A"`:

- vector-only: **HIT** — `['HI-3309-6', 'HI-5502-8', 'MED-0603-A']` (ranked
  3rd, marginally in the top-3)
- BM25-only: **miss** — `['CLM-2026-0412', 'CLM-2026-0520', 'MED-0520-A']`
  (MED-0603-A not in top-3 at all)
- hybrid: **miss** — `['HI-3309-6', 'CLM-2026-0412', 'HI-5502-8']`

## Why — and it's not "which ranking algorithm is better"

```
grep -c "MED-0603-A" data/medical_notes/MED-0603-A.txt   -> 0
grep -c "CLM-2026-0412" data/claims/CLM-2026-0412.txt    -> 1
```

`MED-0603-A.txt`'s own body text **never mentions its own ID** — medical
notes don't self-reference their document ID the way claim narratives and
policy documents do (both were generated with a title line that includes
their own ID). BM25 does pure literal term matching against chunk text, so
if the ID string isn't in the text at all, BM25 has *nothing* to match — its
miss here isn't a ranking weakness, it's a total absence of signal. Vector
search's "hit" was itself marginal (rank 3, behind two unrelated health
insurance policies with no connection to this claim) — plausibly a
coincidental semantic association (embeddings may have learned some vague
"MED-prefixed strings correlate with clinical content" pattern) rather than
a confident, principled match. Hybrid search then combined a real BM25 miss
with a weak vector hit via RRF, and the fusion landed on the wrong side.

**The real lesson: exact identifier lookup isn't a retrieval-*ranking*
problem at all.** When an identifier doesn't reliably appear in a document's
own prose, no method scoring free-text chunk content — semantic or
keyword-based — can be expected to find it reliably. The correct fix isn't
"pick a better ranking method," it's routing an obviously ID-shaped query
(matches a known ID pattern like `[A-Z]{2,3}-\d{4}-\d`) to a **structured
metadata filter** (`WHERE doc_id = 'MED-0603-A'`) instead of semantic or
BM25 search over free text — pgvector's `chunks` table already stores
`doc_id` as its own column specifically for this. This wasn't obvious in
advance; it came out of actually running the test and checking why the
result was surprising, rather than assuming the more sophisticated-sounding
method (hybrid) would automatically be the safest choice.

## A caution about RRF specifically

The golden-set result shows RRF fusion correctly covering for BM25's
weakness. The identifier-lookup result shows the opposite is also possible:
fusing in a ranking that's genuinely uninformative for a given query can
pull the result *away* from what the single best method already had right.
RRF isn't a strict improvement guarantee over "always trust whichever method
handles this query type best" — it's a reasonable default that assumes both
input rankings carry some real signal, which isn't true for every query.

## What's not yet tested

- **Reranking** — the last open item in this phase, and a natural next step
  given the RRF caution above: a reranker scores the fused candidates
  directly against the query, which could catch exactly this kind of
  fusion-picks-the-wrong-answer case.
- **Query routing** — detecting ID-shaped queries and routing them to a
  structured filter wasn't implemented, only diagnosed. Worth doing before
  this becomes the final decision doc's recommendation.

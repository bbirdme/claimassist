# Phase 1: Standing Up pgvector

Mid-phase working document — not the final `docs/phase-1-rag-architecture.md`
decision doc, which comes once the whole phase (hybrid search, reranking
still remain) is done. Companion to
[phase-1-embedding-comparison.md](./phase-1-embedding-comparison.md).

## What was built

- `infra/docker-compose.yml` — `pgvector/pgvector:pg17` (Postgres 17 with the
  pgvector extension), port 5435 (avoiding collision with other local
  Postgres containers on 5432/5433/5434), named volume for persistence.
- `src/retrieval/vector_store.py` — schema, insert, and cosine-similarity
  query functions.
- `src/retrieval/build_index.py` — chunks the full corpus (structural
  chunking), embeds every chunk with Gemini, inserts into pgvector.
- `src/eval/retrieval_eval_pgvector.py` — re-runs the golden-set retrieval
  test through pgvector instead of in-memory numpy, to validate the real
  database path against the earlier prototype.

Since the [embedding comparison](./phase-1-embedding-comparison.md) showed
Gemini clearly outperforming Ollama (100% vs 78.9% hit rate), pgvector is
built around Gemini's embeddings only — a production system settles on one
embedding model, not two running in parallel indefinitely.

## Three real problems hit while building this, not just "it worked"

### 1. pgvector's HNSW index caps at 2,000 dimensions — Gemini's default embedding doesn't fit

`gemini-embedding-001` returns 3,072-dimensional vectors by default (used in
the embedding comparison). Attempting to create an HNSW index on a
`vector(3072)` column fails outright:

```
psycopg.errors.ProgramLimitExceeded: column cannot have more than 2000
dimensions for hnsw index
```

Fix: Gemini's embedding model is trained with Matryoshka representation
learning specifically so it can be *truncated* to a smaller
`output_dimensionality` (1,536 here) without needing to re-train or use a
different model — the API supports this directly via
`EmbedContentConfig(output_dimensionality=1536)`. This is not a workaround
that degrades quality as a side effect; it's a supported feature of this
specific model family. Confirmed below that retrieval quality didn't drop.

### 2. Gemini's free tier allows only 100 embedding requests/minute

Indexing all 118 chunks in one run exceeded the free-tier rate limit
partway through and crashed with a 429. Fixed with a retry-with-backoff
wrapper (`embed_with_retry` in `build_index.py`) that sleeps 60s and retries
on a 429 rather than letting a one-time batch job fail outright. This is a
real constraint worth remembering for Phase 6 (cost/deployment): any batch
re-indexing job at real corpus scale needs either a paid tier, request
throttling, or both.

### 3. `psycopg` doesn't infer the `vector` type from a plain Python list on query parameters

Inserting worked immediately (`register_vector` correctly adapts a Python
list to pgvector's wire format when the target column type is known from
context). Querying with a list as a bound parameter did not:

```
psycopg.errors.UndefinedFunction: operator does not exist: vector <=> double precision[]
```

Fixed by adding an explicit `%s::vector` cast in the SQL itself, rather than
relying on implicit type inference. A small, easy-to-miss integration detail
between an ORM-adjacent library (`pgvector-python`) and raw parameterized
SQL.

## Validation: does the real pgvector path match the in-memory prototype?

| | Dimensions | Index | Hit rate (19 questions) |
|---|---|---|---|
| In-memory (numpy, brute-force) | 3,072 | none (exact) | 100% |
| pgvector (HNSW, approximate nearest neighbor) | 1,536 (truncated) | HNSW | 100% |

Same result despite two changes at once (truncated dimensionality, and an
*approximate* nearest-neighbor index instead of exact brute-force search).
At this corpus size (118 chunks) neither change cost any measurable
retrieval quality. That's expected — HNSW's approximation error and
Matryoshka truncation's information loss both tend to matter more at larger
scale and with finer-grained distinctions than this test currently makes;
this result validates the pipeline is wired correctly, not that these
trade-offs are free at production scale.

## What's not yet tested

- **Scale** — 118 chunks is nowhere near where HNSW's approximate-search
  trade-offs or truncated-dimension quality loss would actually show up.
- **Hybrid search and reranking** — still open items for this phase.
- **Metadata filtering** — the schema stores `doc_type` but nothing in this
  phase has queried with a `doc_type` filter yet (e.g. "only search policy
  documents"), which a real case-worker tool would likely want.

# Phase 1: Embedding Model Comparison

Mid-phase working document — not the final `docs/phase-1-rag-architecture.md`
decision doc, which comes once the whole phase (pgvector, hybrid search,
reranking still remain) is done. Companion to
[phase-1-chunking-strategies.md](./phase-1-chunking-strategies.md).

## Models compared

- **Ollama, `nomic-embed-text`** — 768 dimensions, local, free, no rate limits
- **Gemini, `gemini-embedding-001`** — 3,072 dimensions, hosted, free tier,
  network-dependent

Both mirror the hosted-vs-local pattern from Phase 0. Groq has no embeddings
endpoint, so it isn't part of this comparison.

## Method

1. Chunked the entire 17-document corpus with structural chunking (the
   strategy that came out ahead qualitatively in
   [phase-1-chunking-strategies.md](./phase-1-chunking-strategies.md)) → 118
   chunks total.
2. Embedded every chunk, and all 19 [golden-set](../src/eval/golden_set.py)
   questions, with each model separately (a chunk embedded by one model is
   only ever compared against query embeddings from that same model — the two
   models' vector spaces aren't compatible with each other).
3. For each question, ranked all 118 chunks by cosine similarity to the
   question's embedding, took the top 3, and checked whether any of those 3
   chunks' source document was in the question's known-correct `source_docs`.
   No LLM involved in this step — pure vector similarity, in memory, no
   database yet.

Code: `src/integrations/embedding_providers.py`,
`src/eval/retrieval_eval.py`.

## Results

| Model | Hit rate (top-3, 19 questions) |
|---|---|
| Ollama (`nomic-embed-text`) | **78.9%** (15/19) |
| Gemini (`gemini-embedding-001`) | **100%** (19/19) |

## What Ollama actually got wrong — the pattern matters more than the number

All 4 misses share the same shape: **confusion between multiple similar
documents of the same type**, not random failure.

- **Q03** ("Does Angela Torres's policy HO-1120-7 cover flood damage?") —
  retrieved Maria Gutierrez's policy (HO-88213-4) twice instead of Angela
  Torres's. All 3 homeowners policies share near-identical exclusion
  boilerplate ("Flood damage", "Earth movement", etc.) — Ollama's embedding
  couldn't tell apart two policies whose relevant text is almost the same
  wording, differing mainly in policy number and name.
- **Q04** ("What is the collision deductible on James Whitfield's auto
  policy?") — retrieved two *other* auto policies (Priya Nair's, Marcus
  Webb's) instead of James's own (AU-3387-1). Same failure mode, auto
  policies this time.
- **Q14** ("What diagnosis did Sofia Ramirez receive at the ER?") — retrieved
  her *follow-up* note (MED-0603-A) instead of the actual ER note
  (MED-0520-A). Both notes are about the same wrist fracture for the same
  patient — topically almost identical, differing mainly in visit date and
  specific findings.
- **Q17** (James Whitfield's claim CLM-2026-0412) — retrieved completely
  different claims (Angela Torres's, Priya Nair's), missing James's own claim
  entirely.

**This is exactly the scenario the corpus was deliberately designed to
create** — 3 similar-but-different policies per type, specifically so
retrieval would have something real to get confused by (see the ground-truth
facts in `src/corpus_gen/facts.py`). It worked:
Ollama's smaller, lower-dimensional embedding model appears to cluster
same-topic near-duplicate documents too tightly together, losing the
fine-grained details (a specific policy number, a specific name, a specific
dollar figure) that actually distinguish them. Gemini's larger model captured
those distinctions perfectly, in every single case.

## This is a real trade-off, not just "Gemini wins"

- **Gemini**: perfect retrieval here, but real cost at scale (see Phase 0's
  per-token pricing math), a network round-trip per embedding call, and
  subject to free-tier rate limits.
- **Ollama**: free forever, fully local, no rate limits, no network
  dependency at all — but measurably worse at distinguishing near-duplicate
  documents on this corpus.

For a real ClaimAssist deployment, this is exactly the kind of decision that
belongs in the final architecture doc: if the corpus realistically contains
many similar documents (multiple policies of the same type, multiple visits
for the same patient — which real insurance/healthcare data absolutely does),
retrieval precision on near-duplicates may be worth paying for. If cost,
privacy, or offline operation matters more than that specific failure mode,
a local model may be an acceptable trade rather than a strict downgrade.

## Limitations of this test

- **Top-3, single run** — no repeated sampling, no sensitivity check on `k`.
- **Lenient hit definition** — "hit" means any of the top-3 chunks' *document*
  matches a known-correct source, not that the single best-matching *chunk*
  was retrieved, and not that a generated answer using that chunk would
  actually be correct. Full answer-quality evaluation (retrieve → generate →
  judge) is a further step, not done here.
- **One chunking strategy tested** — all 118 chunks came from structural
  chunking. Whether fixed-size or semantic chunking would change which model
  wins, or by how much, hasn't been tested.
- **No hybrid search or reranking yet** — both still open items for this
  phase; either could plausibly narrow or widen the gap seen here.

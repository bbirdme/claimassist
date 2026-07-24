# Phase 1: RAG Architecture

Full working detail for each piece of this phase lives in its own doc:
[phase-1-chunking-strategies.md](./phase-1-chunking-strategies.md),
[phase-1-embedding-comparison.md](./phase-1-embedding-comparison.md),
[phase-1-pgvector.md](./phase-1-pgvector.md),
[phase-1-hybrid-search.md](./phase-1-hybrid-search.md),
[phase-1-reranking.md](./phase-1-reranking.md). This doc is the synthesis:
what was ultimately chosen, why, and what's honestly still missing.

## Decision

- **Corpus**: 17 synthetic documents (9 policies across 3 types, 5 claims,
  3 medical notes), authored as ground-truth facts first and expanded into
  realistic prose via Ollama — not the reverse — so retrieval quality could
  be measured against known-correct answers, not eyeballed. Policy documents
  rendered as multi-page PDFs; 3 of them additionally simulated as scanned
  images requiring OCR fallback.
- **Chunking**: structural (section-header-based for policies,
  paragraph-based for claims/notes), chosen over fixed-size and semantic.
- **Embedding model**: Gemini's `gemini-embedding-001`, truncated to 1,536
  dimensions, chosen over Ollama's local `nomic-embed-text`.
- **Vector store**: pgvector (Postgres 17), HNSW index, cosine similarity.
- **Retrieval**: hybrid search — vector similarity + BM25, combined via
  Reciprocal Rank Fusion.
- **Reranking**: LLM-based listwise reranking (Groq), included but flagged
  as a genuine trade-off rather than an unconditional recommendation — see
  below.

## Alternatives considered

- **Fixed-size chunking** — simplest, but reliably broke mid-word and mixed
  unrelated content across page breaks (see chunking doc, Findings 1 & 4).
- **Semantic chunking** — theoretically the most adaptive, but a single
  similarity threshold couldn't separate "different section" from "same
  section, natural variance" in formal, stylistically uniform text (Finding
  7) — collapsed a 6-section policy document into 2 giant chunks.
- **Ollama's local embedding model** — free, local, no rate limits, and
  seriously considered for exactly those reasons. Rejected because it hit
  78.9% vs. Gemini's 100% on the golden set, and every miss followed the
  same pattern: confusing between multiple similar documents of the same
  type — precisely the failure mode a real ClaimAssist corpus (many
  policies of the same type, many visits for the same patient) would
  actually contain.
- **Skipping OCR entirely** — would have been simpler, but a real insurance
  operation has scanned/legacy paperwork; testing the detect-and-fallback
  extraction logic against a real (if simulated) scanned document was worth
  the added complexity.
- **A dedicated cross-encoder reranker** — the textbook approach, actually
  attempted first. Abandoned after `sentence-transformers` pulled in a
  4.9GB CUDA build of PyTorch with no GPU to use it. Pivoted to LLM-based
  reranking instead, which needed no new heavy dependency and reused
  existing provider code.
- **No reranking at all** — a real option. Reranking didn't improve the net
  hit rate on either test set (23/24 hits with or without it, just
  different queries succeeding) — see below.

## Why

- **Zero-budget constraint** (carried over from Phase 0) drove every
  provider choice: Gemini, Groq, and Ollama only, no Claude/OpenAI. This
  also directly caused two real engineering problems worth remembering —
  Gemini's `generateContent` free tier caps at 20 requests/**day** (not
  per-minute) and its embedding endpoint at 100/minute, both of which broke
  batch jobs that weren't written with retry/backoff in mind.
- **Corpus size and realism were chosen deliberately, not arbitrarily**:
  documents were sized and structured (multi-page, tables, near-duplicate
  policies of the same type) specifically to make chunking/embedding/hybrid
  search differences *visible*, rather than using trivial documents where
  every method would trivially succeed. This paid off directly — the
  embedding comparison, hybrid search test, and reranking test all
  surfaced real, specific failure patterns rather than abstract ones.
- **Data sensitivity**: this is a fictional regulated-healthcare-adjacent
  system. Free-tier hosted APIs commonly reserve rights to use submitted
  prompts for training/review — a real production system handling actual
  claim data would need to weight this against Phase 4's eventual security
  requirements, not just cost.
- **Client type**: a case worker needs both semantic lookup ("what's covered
  here") and exact lookup ("find claim CLM-2026-0412"). The identifier
  lookup test specifically probed the second need, and the answer that
  emerged — route exact IDs to structured metadata filtering, not ranking
  algorithms — is a direct, practical architecture recommendation the
  original phase plan didn't anticipate needing.

## What I'd change at real production scale

- **Include Claude and/or OpenAI** in the embedding and generation
  comparisons. The zero-budget constraint is a known, self-imposed gap, not
  a real conclusion that Gemini/Groq/Ollama are sufficient.
- **Test at real corpus scale.** 118 chunks is nowhere near where HNSW's
  approximate-search trade-offs or the 3072→1536 dimension truncation's
  information loss would actually show a measurable cost. The current
  validation (pgvector matched the in-memory prototype exactly) proves the
  pipeline is wired correctly, not that these trade-offs are free at scale.
- **Add structured metadata filtering for exact identifiers**, rather than
  relying on reranking to paper over what vector/BM25 search structurally
  can't do. This is the single most concrete, actionable finding from this
  phase and hasn't been implemented yet, only diagnosed.
- **Re-evaluate reranking with a much larger, harder test set** before
  deciding whether to keep it in production. On this corpus it was a wash
  (one fix, one regression) — not enough evidence either way, and the extra
  LLM call per query has real latency and cost implications at volume.
- **Build a genuinely larger golden set** (this is exactly what Phase 5
  formalizes). With only 19 golden-set questions and 5 identifier queries,
  most methods hit ceiling effects (100%) that make it hard to tell "this
  method is actually better" from "this test isn't hard enough to
  differentiate them."
- **Handle rate limits as a production concern, not a workaround.** Every
  free-tier limit hit in this phase (embedding RPM, generateContent daily
  cap) was patched with retry/backoff for a one-time batch job. A real
  production system needs either a paid tier sized to real traffic, or
  deliberate request throttling/queueing designed in from the start.
- **Revisit free-tier data-handling terms** before this pipeline ever
  touches non-synthetic data, regardless of how good the retrieval numbers
  look.

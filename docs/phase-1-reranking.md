# Phase 1: Reranking

Mid-phase working document — the last one before the final
`docs/phase-1-rag-architecture.md` decision doc, which synthesizes this
whole phase. Companion to
[phase-1-hybrid-search.md](./phase-1-hybrid-search.md).

## What was built

`src/retrieval/llm_rerank.py` — **listwise LLM reranking**: hybrid search's
top-10 candidates are shown to an LLM in a single prompt, which scores each
0–10 for relevance to the query and returns the top 3 by score. One call
sees all candidates together (rather than scoring each independently), so it
can judge relevance *relative to the other candidates*, not just in
isolation.

A cross-encoder model (the textbook approach — see the earlier conceptual
discussion) was the original plan, but installing `sentence-transformers`
pulled in a 4.9GB CUDA build of PyTorch with no GPU on this machine to use
it - fixed at the time by pointing `uv` at PyTorch's CPU-only wheel index
rather than abandoning the approach outright, a real, easy-to-miss
dependency-hygiene issue worth knowing about (`[tool.uv.sources]` +
`[[tool.uv.index]]` in `pyproject.toml`, pointing `torch` at
`https://download.pytorch.org/whl/cpu`). Reranking itself ended up
implemented via LLM prompting instead of the cross-encoder, after hitting
Gemini's free tier's **20 requests/day** cap on `generateContent` (a daily
limit, not per-minute - retrying with backoff doesn't help against that).
Switched the reranker to Groq, which had no such daily cap in Phase 0's
testing. Since the shipped reranker (`src/retrieval/llm_rerank.py`) only
calls Groq via prompting, `sentence-transformers`/`torch` aren't actually
dependencies of the final approach - they were removed rather than kept
as unused weight once the LLM-prompting path worked.

## Results

| Test set | Hybrid only | Hybrid + LLM rerank |
|---|---|---|
| Golden set (19 questions) | 100% (19/19) | **95% (18/19)** |
| Identifier lookup (5 queries) | 80% (4/5) | **100% (5/5)** |

Net across both sets combined: 23/24 hits either way. Reranking didn't
improve the aggregate hit rate — it **traded one failure for a different
one**.

### The regression: reranking got a correct answer wrong

*"What is the collision deductible on James Whitfield's auto policy?"*
(correct answer: policy AU-3387-1)

- Hybrid only: **HIT** — `['CLM-2026-0412', 'CLM-2026-0412', 'AU-3387-1']`
  (James's own policy correctly in the top 3)
- With rerank: **miss** — `['AU-7742-5', 'AU-2298-3', 'CLM-2026-0412']`
  (James's policy demoted out; two *other* people's auto policies promoted
  in instead)

All 3 auto policies share very similar structure and language ("collision
deductible: $X"), which is exactly the near-duplicate-document scenario this
corpus was deliberately built to expose (see
[phase-1-embedding-comparison.md](./phase-1-embedding-comparison.md)). Here,
the reranker's listwise judgment picked the wrong policies among a set of
structurally similar candidates — a new failure mode this component
introduced, not one it inherited from an earlier stage.

### The fix: reranking recovered the earlier identifier-lookup miss

*Query: `"MED-0603-A"`* (correct answer: MED-0603-A itself)

- Hybrid only: **miss** — `['HI-3309-6', 'CLM-2026-0412', 'HI-5502-8']`
- With rerank: **HIT** — `['MED-0603-A', 'HI-3309-6', 'CLM-2026-0412']`

This is the exact case [phase-1-hybrid-search.md](./phase-1-hybrid-search.md)
documented as unsolvable by ranking algorithms alone, since `MED-0603-A.txt`
never mentions its own ID in its body text. So why did reranking fix it?

**Because the reranker's prompt shows each candidate's `doc_id` label
directly** (`_format_passages` builds `"(doc: {doc_id})\n{text}"` per
candidate). Vector search and BM25 only ever matched against `chunk_text` —
neither one ever "saw" the doc_id as searchable content. The LLM reranker,
given the literal query `"MED-0603-A"` next to a candidate list explicitly
labeled `(doc: MED-0603-A)`, could match the two directly. **This isn't
evidence the reranker "reasoned better" about relevance** — it succeeded
because it had access to information the earlier stages structurally
couldn't use for matching. That's a legitimate, real architectural lesson,
just a different one than "add a reranker and it gets smarter":  **making
identifying metadata visible to whatever component does the final relevance
judgment can close a gap that pure content-based search cannot** — whether
that component is a reranker or (more directly, and more in line with the
prior doc's recommendation) a structured `WHERE doc_id = ...` filter.

## What this means for the recommendation

Reranking is not a strict improvement here — it's a genuine trade-off
between two different failure modes, on a corpus this small (118 chunks, 24
test queries). Whether to include it in a production system depends on
which error is worse in practice: missing a paraphrased semantic question,
or picking the wrong document among several structurally similar ones. This
test size can't settle that generally; it can only show that "add a
reranker" isn't automatically a net win, which is itself worth knowing before
committing to the extra latency and cost of one more LLM call per query.

## What's not yet tested

- **The cross-encoder approach originally planned** — not built, since the
  LLM-reranking pivot answered the phase's "try reranking" requirement
  without the dependency overhead. Whether a dedicated cross-encoder would
  avoid the auto-policy regression seen here is untested.
- **Whether including doc_id/title metadata directly in vector and BM25
  matching** (not just the LLM reranker's prompt) would close the identifier
  gap without reranking's added cost — a cheaper fix worth trying before
  reranking, per the note above.

# Phase 1: Chunking Strategies — Working Notes

This is a mid-phase working document, not the final Phase 1 decision doc.
Phase 1 is still in progress (embeddings, pgvector, hybrid search, and
reranking are not built yet) — this captures what's been verified so far on
chunking, using the real synthetic corpus (see
[phase-0-provider-comparison.md](./phase-0-provider-comparison.md) and the
`data/` directory for corpus details). The final `docs/phase-1-rag-architecture.md`
decision doc will be written once the whole phase is done, following this
project's standard decision-doc format.

## The three strategies

1. **Fixed-size** — a sliding window over raw characters (500 chars, 50-char
   overlap in this test). No awareness of sentences, sections, or any other
   structure. The simplest possible baseline.
2. **Structural** — splits on the document's own structure: for policy
   documents, our known section headers (DECLARATIONS, COVERAGE SUMMARY,
   DEDUCTIBLES AND LIMITS, EXCLUSIONS, DEFINITIONS); for claims and medical
   notes, which don't have rigid sections, paragraph boundaries (blank lines).
3. **Semantic** — groups consecutive sentences by embedding similarity,
   starting a new chunk when similarity between adjacent sentences drops
   below a threshold (0.5 in this test). Uses Ollama's local embedding model
   (free, no rate limits) purely for the chunking mechanism itself, separate
   from the 2 embedding models being compared for retrieval in
   [phase-1-embedding-comparison.md](./phase-1-embedding-comparison.md).

Code: `src/ingestion/chunking/fixed_size.py`,
`src/ingestion/chunking/structural.py`, `src/ingestion/chunking/semantic.py`,
run against the real corpus via `src/ingestion/chunking/compare.py`.

## Test case 1: HO-88213-4 (policy document, 2,248 chars, direct PDF extraction)

**Fixed-size — 5 chunks:**

| # | Chars | Starts with |
|---|---|---|
| 0 | 500 | `HO-88213-4 — Page 1\n Policy Document — HO-88213-4\nDECLARATIONS\n...` |
| 1 | 500 | `y purpose is\nto protect Maria Gutierrez against unforeseen losses...` |
| 2 | 500 | `dence)\nWear, tear, and gradual deterioration\nMold, except when...` |
| 3 | 500 | `e is\n$1,000.\n\nHO-88213-4 — Page 2\n* Dwelling Coverage:...` |
| 4 | 446 | `from covered water damage.\nBy signing below, Maria Gutierrez...` |

**Structural — 6 chunks:** one per section, cleanly isolated (title line,
DECLARATIONS, COVERAGE SUMMARY, DEDUCTIBLES AND LIMITS, EXCLUSIONS,
DEFINITIONS), sized 48–1,199 chars each.

### Finding 1: fixed-size breaks mid-word and mixes unrelated sections

Chunk 2 literally starts `"dence)\nWear, tear..."` — cut off mid-word from
"subsidence)". Chunk 3 is worse: it spans across the exclusions→definitions
*page break*, splicing the tail of the deductibles schedule together with the
page-2 header and the start of an unrelated definition:
`"...is\n$1,000.\n\nHO-88213-4 — Page 2\n* Dwelling Coverage:..."`. That's a
single retrieval chunk containing two semantically unrelated facts — exactly
the failure mode structural chunking is supposed to avoid.

### Finding 2: structural chunking has its own real cost — uneven chunk size

The DEFINITIONS chunk came out at 1,199 characters, bundling all 4 term
definitions (Deductible, Dwelling Coverage, Coinsurance, Water Damage) into
one chunk. That means a query asking specifically "what is a deductible?"
retrieves the *entire* definitions block — including irrelevant Coinsurance
and Water Damage definitions — diluting precision. Structural chunking traded
one failure mode (broken mid-section chunks) for another (coarse-grained,
oversized chunks when a section happens to be long).

### Finding 3: table extraction is messy regardless of chunking strategy

The deductibles table, extracted via `pypdf`, comes out flattened with column
structure lost: `"Item\nAmount\nSchedule of Deductibles and Limits\nStandard
Deductible\n$1,000\nWind/Hail Deductible\n$..."`. This happens at the
*extraction* stage, before either chunker even runs — no chunking strategy can
fix data that's already lost its row/column structure by the time it reaches
the chunker. Worth keeping separate from the chunking comparison when judging
which strategy is "better."

## Test case 2: CLM-2026-0412 (claim narrative, 1,302 chars, plain text)

**Fixed-size — 3 chunks**, each ~500 chars, no structure awareness.

**Structural (paragraph-based) — 5 chunks**, one per paragraph, each a
complete, coherent unit (e.g. one chunk is entirely "the vehicle damage and
repair estimate" facts, another is entirely "the injury and medical note"
facts).

### Finding 4: fixed-size's mid-word problem isn't policy-specific

Chunk 1 starts `"ont-end damage..."` — cut from "front-end damage". Same
failure mode as the policy document, on a completely different document type.
This isn't a quirk of PDF extraction or tables — it's inherent to splitting
on a raw character count with no regard for word or sentence boundaries.

### Finding 5: paragraph-based structural chunking works well when the source document's own paragraph breaks align with distinct facts

Because the claim narrative was generated with one fact-cluster per
paragraph (vehicle damage, then the injury/medical note), paragraph-boundary
chunking produced clean, single-topic chunks without needing the rigid
section headers policy documents have. This is encouraging for claims/medical
notes specifically, but it's worth being honest that this depended on the
generated prose happening to paragraph-break in the right places — not a
structural guarantee the way section headers are for policy documents.

## Semantic chunking: two real findings, one bug and one genuine limitation

Running semantic chunking on the same two documents surfaced two problems —
one was a bug worth fixing, the other is a real limitation worth keeping.

### Finding 6 (bug, fixed): naive sentence splitting breaks on abbreviations

The first version of the sentence splitter produced a chunk that was
literally `"Mr."` — 3 characters — because a period-based regex treated "Mr."
as a sentence boundary, splitting "Mr. Whitfield" into two fake sentences.
Fixed by merging fragments that end in a common abbreviation (Mr., Dr., Inc.,
etc.) back into the next fragment before treating a period as a true sentence
end. This is a well-known class of bug with naive sentence splitters; a real
NLP tokenizer (spaCy, etc.) handles it more generally, which wasn't worth the
extra dependency for this test.

### Finding 7 (real limitation, not fixed): a single similarity threshold can't separate "different section" from "same section, natural variance"

For HO-88213-4, semantic chunking collapsed almost the entire document into
2 giant chunks (1,826 + 419 chars) — far coarser than structural chunking's 6
sections. Inspecting the actual sentence-to-sentence cosine similarities
explains why: cross-section transitions scored 0.54–0.70, but *within-section*
sentence pairs scored as low as 0.54–0.58 too (e.g. between two different
term definitions inside the same DEFINITIONS section). The only similarity
score that stood out clearly was 0.380, at the transition into the closing
signature/boilerplate block — a genuinely different register, not just a
different topic.

In formal, stylistically uniform documents like insurance policies, sentences
share enough vocabulary and register that a single global similarity
threshold can't reliably separate "topic changed" from "still the same topic,
just naturally varied wording." This wasn't cherry-picked away by tuning the
threshold — the actual overlap between within-section and cross-section
similarity scores means no single fixed threshold would cleanly separate them
for this document. A more robust approach would likely combine structural
boundaries (hard section breaks) with semantic similarity only *within* a
section for finer splits, rather than relying on semantic similarity alone
across an entire document.

For the claim narrative, semantic chunking did better — 3 chunks, including
isolating `"However, as per policy terms, a collision deductible applies to
this claim."` as its own chunk, a genuinely sensible boundary (a short
transitional/procedural sentence between the vehicle-damage description and
the injury description). Shorter, less formulaic prose seems to give the
threshold-based approach a better chance.

## What's not yet tested

- **Chunk size sensitivity** — this test used 500 chars for fixed-size
  arbitrarily; smaller windows would reduce the mid-word problem's *visual*
  severity but not eliminate it, and would increase total chunk count (more
  embedding cost). Not yet measured.
- **Retrieval quality impact** — none of this has been run through actual
  embedding + retrieval yet against the golden set
  ([golden_set.py](../src/eval/golden_set.py)). Everything above is a
  structural/qualitative comparison of chunk boundaries, not a measurement of
  which strategy actually answers more golden-set questions correctly. That's
  the next real test, once embeddings exist.

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
3. **Semantic** — not yet implemented. Requires sentence embeddings to detect
   topic shifts, so it's being built alongside the embedding-model comparison
   step next, rather than as a separate one-off.

Code: `src/ingestion/chunking/fixed_size.py`,
`src/ingestion/chunking/structural.py`, run against the real corpus via
`src/ingestion/chunking/compare.py`.

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

## What's not yet tested

- **Semantic chunking** — pending, to be built alongside embeddings.
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

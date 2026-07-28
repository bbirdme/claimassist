# Phase 2: Single-Agent Claim Lookup + Discrepancy Check

Mid-phase working document — not the final `docs/phase-2-agent-architecture.md`
decision doc, which comes once the multi-agent (LangGraph) comparison and
human-in-the-loop step are also done.

## What was built

- `src/agents/tools.py` — 3 structured lookup tools (`lookup_claim`,
  `lookup_policy`, `lookup_medical_notes`), deliberately *not* semantic
  search — Phase 1 already established that exact-identifier lookups belong
  on structured data, not ranking algorithms (see
  [phase-1-hybrid-search.md](./phase-1-hybrid-search.md)).
- `src/agents/single_agent.py` — a hand-rolled tool-calling loop (no
  framework — LangGraph is reserved for the multi-agent step) using Groq's
  `llama-3.3-70b-versatile`, which supports native function calling. The
  agent is instructed to check: date of loss within the policy's effective
  period, loss type not excluded, and (for injury claims) medical notes
  consistent with the claim narrative — then return structured JSON.
- `src/agents/deterministic_check.py` — the same date-range and exclusion
  checks, implemented as plain Python, no LLM involved.

## Test 1: reliability on a known-clean claim

`CLM-2026-0301` has zero real discrepancies, by construction (verified
against the ground-truth facts in `src/corpus_gen/facts.py`: the date of
loss falls inside the policy period, and wind/hail is not on the exclusion
list). Running the *identical* task 10 times:

| Outcome | Count |
|---|---|
| Correct (no discrepancies) | 2/10 |
| False positive | 7/10 |
| Crashed | 1/10 |

Two distinct, *recurring* failure patterns — not one-off noise:

- **Backwards date reasoning** (3 runs): *"the date of loss (2026-03-03) is
  after the policy expiration date (2026-09-01)"* — March is not after
  September. One of these three runs also hallucinated a completely
  different, wrong expiration date (2026-02-28) to justify the same wrong
  conclusion.
- **Hallucinated reference ID** (4 runs): the model invents a policy number
  that appears nowhere in the actual data (e.g. `HO-12345-1`), attributes it
  to "the claim," then reports a "mismatch" between its own invention and
  the real policy number it separately looked up correctly. This happened 4
  times independently, always with a similarly generic placeholder-shaped
  fake ID.
- **Tool-calling protocol failure** (1 run): the model emitted
  hand-written pseudo-syntax (`<function=lookup_claim,{...}</function>`)
  instead of using the actual structured tool-calling protocol, which Groq's
  API rejected outright.

## Test 2: does it catch *real* discrepancies?

Two synthetic broken cases (`src/eval/broken_claim_cases.py`, not added to
the real corpus) were built specifically to check the agent isn't just
"quiet by default" — one with a date a full year outside the policy period,
one with an explicitly excluded loss type (flood). 3 runs each:

| Case | Caught | Crashed |
|---|---|---|
| Date outside policy period | 3/3 | 0/3 |
| Excluded loss type (flood) | 2/3 | 1/3 (malformed JSON output) |

Better than the clean-claim test — an obviously wrong date or an exact
string match against "Flood damage" gives the model a much stronger signal
to latch onto. But even the *successful* runs weren't clean:

- One run correctly caught the date issue, then also hallucinated a second,
  fake discrepancy: *"the policy number (POLICY-001) does not exist"* — the
  same hallucinated-reference-ID pattern from Test 1, this time appended
  alongside a genuinely correct finding rather than replacing it.
- Another run added hedgy, non-committal language around a real finding:
  *"loss type potentially excluded... may be partially or fully excluded
  under certain conditions"* — not wrong, but not the crisp, actionable
  statement a case worker needs either.
- The one crash was a *different* failure mode than Test 1's: not a
  tool-calling protocol error, but a malformed JSON escape sequence in the
  final answer, breaking `json.loads()`.

**Even when the agent gets the headline finding right, its output still
needs a human to separate the real signal from hallucinated noise.**

## The deterministic comparison

`src/agents/deterministic_check.py` performs the same two checks (date
range, exclusion match) with plain code:

- All 5 real claims, run 3 times each (15 total): **15/15 correct**,
  identical result every time.
- Both synthetic broken cases: **caught every time**, instantly, no API
  call.

**Being honest about the deterministic side too**: this didn't work
perfectly on the first attempt either. A naive substring match against
`CLM-2026-0214` (a real water-damage claim) initially produced its own false
positive — matching "water damage" inside the exclusion clause *"Mold,
except when directly resulting from a covered water damage event"*, missing
that the clause's actual meaning is the opposite of what the substring
match implied (mold is excluded except when caused by water damage; water
damage itself isn't excluded at all). Fixed by explicitly handling the
"except" qualifier.

The difference that matters: **the deterministic code's failure was one
specific, identifiable logic bug, fixed once, and now correct forever.**
The agent's failures are not fixable the same way — they recurred
differently across independent runs of the *identical* input, with no
single bug to patch.

## What this suggests, going into the multi-agent comparison

This isn't really "deterministic code beats agents" as a blanket claim — the
date-range and exact-string-match exclusion checks are precisely the kind of
task deterministic code is built for: unambiguous, structured data, one
correct answer. Where an LLM might still earn its place is exactly where
this deterministic check is weakest by design — interpreting genuinely
ambiguous or novel exclusion language, or writing the human-readable summary
for a case worker. A hybrid design (deterministic checks for well-defined
rules, LLM only for genuinely open-ended judgment and the final write-up)
is the natural next thing to test, rather than treating "agent vs.
deterministic" as all-or-nothing.

## What's not yet tested

- **Medical note consistency check** — the system prompt asks the agent to
  verify injury claims against linked medical notes, but no test case
  specifically exercised this yet.
- **The multi-agent (LangGraph) version** — next step in this phase.
- **Human-in-the-loop approval** — not yet built.

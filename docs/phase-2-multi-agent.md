# Phase 2: Multi-Agent (LangGraph) Comparison

Mid-phase working document — not the final `docs/phase-2-agent-architecture.md`
decision doc, which comes once human-in-the-loop approval is also built.
Companion to [phase-2-single-agent.md](./phase-2-single-agent.md).

## What was built

`src/agents/multi_agent.py` — a LangGraph pipeline with 3 narrowly-scoped
steps, replacing the single agent's one do-everything loop:

1. **Fact Gatherer** — plain code, not an LLM. There's no judgment involved
   in "should I look up the policy" for a known claim ID — all three pieces
   of data are always needed, so there's nothing for an agent to decide.
   This also removes the single agent's most damaging failure mode by
   construction: it can't hallucinate a fake policy number as a tool
   argument, because the real one is passed along in state rather than
   re-typed from memory by an LLM.
2. **Discrepancy Checker** — an LLM call (Groq, same model as the single
   agent), given the already-gathered facts, with no tool calls to make -
   purely reasoning over data it's handed directly.
3. **Summarizer** — an LLM call that writes the case-worker-facing summary
   from the findings.

Built via `langchain-openai`'s `ChatOpenAI`, not `langchain-groq`: the
latter caps its `groq` dependency below `1.0`, which conflicts with the
`groq>=1.5.0` already used everywhere else in this project. Since Groq
exposes an OpenAI-compatible API, pointing `ChatOpenAI` at Groq's endpoint
sidesteps the conflict entirely without downgrading anything.

## The hypothesis this was meant to test

The single agent's errors (see
[phase-2-single-agent.md](./phase-2-single-agent.md)) often came from
juggling tool-calling, reasoning, and summarizing all in one loop —
hallucinating tool arguments, mixing correct findings with invented extras.
Would separating those responsibilities into narrower-scoped steps reduce
the error rate?

## What actually happened: 3 rounds, 3 different failure modes

Same reliability test as the single agent (`CLM-2026-0301`, known from
ground truth to have zero real discrepancies, 10 identical runs):

| Round | Result | What went wrong |
|---|---|---|
| 1 (first prompt) | **0/10 correct** | Model padded the discrepancies list with *confirmations* disguised as issues - e.g. `{"issue": "None of the conditions were met to report a discrepancy", ...}` - despite the prompt saying "if none, respond with exactly `[]`". The underlying reasoning was usually correct; the model just couldn't express "nothing is wrong" as an empty list. |
| 2 (after explicit "do not confirm passing checks" instruction) | **2/10 correct** | That specific bug disappeared entirely - but a new one took its place: 8/10 runs claimed the deductible should already be subtracted from the claim's "total estimated repair cost" figure, a genuine misunderstanding of standard insurance terminology (that figure is the gross estimate; the deductible applies at payout, not before). Consistent, near-identical wording across independent runs - not random noise, a real misconception. |
| 3 (after explicit clarification about deductible timing) | **10/10 correct** | — |

Verified round 3's fix didn't overcorrect into under-reporting real problems:
re-ran the same 2 synthetic broken cases from
[phase-2-single-agent.md](./phase-2-single-agent.md) (date outside policy
period, excluded loss type) - **6/6 caught**, no crashes, no hallucinated
extras. Also re-ran the final prompt against the other 4 real claims (not
just the one used for iteration) - all 4 correctly returned zero
discrepancies, confirming the fixes generalized rather than being tuned to
one claim's specific phrasing.

## What this means: narrower scoping helped with one failure mode, not all of them

Splitting fact-gathering out into plain code did exactly what it was
supposed to: **the multi-agent pipeline never once hallucinated a fake
reference ID**, across any test in this document - the single agent's most
damaging, hardest-to-fix failure mode (4/10 runs on the clean claim, plus a
recurrence in the broken-date test) simply can't happen here, by
construction, because the LLM never has to re-type an ID it already saw.

But narrower scoping alone didn't produce a reliable agent on the first try
- it just meant the *remaining* LLM step failed in different ways
(confirmation-padding, then a domain misconception) that needed the same
kind of iterative prompt debugging the single agent would have needed too.
**Splitting responsibilities changes which failures show up; it doesn't
skip the need to find and fix them.**

## Comparison so far

| Approach | Clean claim (10 runs) | Broken cases (6 runs) | Crashes |
|---|---|---|---|
| Deterministic (no LLM) | 15/15 correct (across all 5 real claims, repeated) | 2/2 caught | 0 |
| Single agent | 2/10 correct | 5/6 caught | 2 (different modes) |
| Multi-agent (final prompt) | 10/10 correct | 6/6 caught | 0 |

The multi-agent version is a real improvement over the single agent on this
task - but it took 3 iterations of prompt debugging to get there, and the
deterministic version was still both correct and free from the start, for
the two checks (date range, exclusion match) that don't actually need
language understanding. The multi-agent architecture's real advantage
showed up structurally, not just in the pass rate: removing tool-calling
from the LLM's job eliminated an entire category of failure by design,
rather than by better prompting.

## What's not yet tested

- **Human-in-the-loop approval** - the last open item before the final
  decision doc.
- **A genuinely harder discrepancy case** - both broken test cases so far
  are fairly clear-cut (an obviously wrong date, an exact exclusion string
  match). Whether the discrepancy-checking step holds up on more ambiguous
  cases (partial exclusion overlap, a borderline date) is untested.

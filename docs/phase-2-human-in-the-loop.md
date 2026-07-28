# Phase 2: Human-in-the-Loop Approval

Mid-phase working document — the last one before the final
`docs/phase-2-agent-architecture.md` decision doc, which synthesizes the
whole phase. Companion to
[phase-2-multi-agent.md](./phase-2-multi-agent.md).

## What was built

`src/agents/human_in_the_loop.py` adds an approval step to the multi-agent
pipeline, between the Discrepancy Checker and the Summarizer, using
LangGraph's built-in **interrupt/resume** primitives (`interrupt()` plus a
checkpointer) rather than a hand-rolled pause loop:

1. `start_review(graph, claim_id)` runs the graph up to `human_review`,
   which calls `interrupt(...)` — execution pauses there, and the proposed
   discrepancies are returned to the caller instead of proceeding straight
   to the summary.
2. A human (in this repo, a script standing in for a real reviewer UI)
   inspects the proposal and decides what to actually approve.
3. `resume_review(graph, config, approved_discrepancies)` resumes the exact
   paused run with the human's decision, which then flows into the
   Summarizer — so the case-worker-facing summary is written from what the
   human approved, not from the agent's raw output.

This matters given [phase-2-multi-agent.md](./phase-2-multi-agent.md)'s own
findings: even the tuned pipeline (10/10 on the test claim) isn't proven
correct on harder cases. A human reviewing before the summary is finalized
is the actual safety net this phase needs, not just a checklist item.

## Testing it on a genuinely ambiguous case, not another clear-cut one

Built a new synthetic claim, `TEST-AMBIG-001`: vandalism damage, $800 repair
estimate, against a policy whose exclusions list has no explicit "vandalism"
entry — genuinely ambiguous, since these policies only list exclusions, and
"vandalism" being absent from that list could plausibly (and correctly)
mean "covered," or an LLM might get confused and treat "not explicitly
covered" as a red flag - a version of the exact failure mode from the very
first single-agent test in
[phase-2-single-agent.md](./phase-2-single-agent.md).

That specific failure didn't reproduce. Instead, something more interesting
came up across several runs: the model organically surfaced a genuinely
useful finding **nothing in the system prompt asked it to check** - the
$800 repair estimate is *below* the $1,000 standard deductible, meaning the
claim would result in **zero payout**. That's real, actionable information
a case worker would want, discovered without being explicitly requested.

## But the output still needed a human editor, not just a rubber stamp

One captured run proposed 3 items, and only 1 was an actual finding:

| Proposed | Verdict |
|---|---|
| "Policy expires soon on 2026-09-01, which may cause issues if repairs are delayed" | **Rejected** - speculative, not an actual problem with the claim *as filed* |
| "Vandalism may be considered an intentional act... but the facts do not indicate the insured was involved" | **Rejected** - labels itself an "issue" while its own explanation concludes it isn't actually excluded; a subtler version of the confirmation-padding bug from phase-2-multi-agent.md, now hiding inside otherwise-reasonable-sounding hedge language instead of an obvious `"no discrepancy found"` entry |
| "The standard deductible of $1,000 exceeds the $800 repair estimate, which may result in no payout" | **Approved** - the real, useful finding |

Running this through `resume_review` with only the approved item confirmed
the final summary reflects the **human's** decision, not the agent's raw
proposal - the actual point of this step, not just "the graph pauses
somewhere."

Interestingly, a separate live run on the same ambiguous claim handled the
"was this intentional" question *better* - phrasing it as an open question
("not clear if the insured was involved") rather than a self-contradicting
false claim. That inconsistency is itself informative: this specific
ambiguity is genuinely borderline enough that the model's phrasing of it
varies run to run, which is exactly the kind of case a human reviewer
should be looking at rather than trusting either version blindly.

## What this establishes for the final decision doc

- The interrupt/resume mechanism works correctly: a paused run can be
  resumed with human-supplied data that measurably changes the final
  output, using LangGraph's actual primitives rather than a hand-rolled
  workaround.
- The confirmation-padding bug from
  [phase-2-multi-agent.md](./phase-2-multi-agent.md) wasn't fully
  eliminated by the earlier prompt fix - it resurfaced in a subtler form on
  a harder case (an item that contradicts its own stated reasoning), which
  is exactly the kind of thing prompt-tuning against one test claim can
  miss and a human review step is positioned to catch.
- The agent also surfaced a genuinely valuable, unprompted insight
  (deductible exceeds estimate) that the deterministic checker
  ([phase-2-single-agent.md](./phase-2-single-agent.md)) doesn't check for
  at all - a real point in favor of keeping an LLM in the loop for
  open-ended review, specifically paired with human oversight rather than
  as a fully autonomous decision-maker.

## What's not yet tested

- **A reviewer UI** - this is a scripted stand-in for human judgment, not
  an actual interface. The mechanism (interrupt/resume) is real; the
  "human" here is still code making a decision, just decoupled from the
  agent's own output.
- **Editing rather than only approve/reject** - the demo only filters the
  proposed list down; a real reviewer might also rewrite an entry's wording
  rather than just keep-or-drop it.

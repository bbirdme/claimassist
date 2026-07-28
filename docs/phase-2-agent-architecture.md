# Phase 2: Agent Architecture

Full working detail lives in its own doc per piece:
[phase-2-single-agent.md](./phase-2-single-agent.md),
[phase-2-multi-agent.md](./phase-2-multi-agent.md),
[phase-2-human-in-the-loop.md](./phase-2-human-in-the-loop.md). This doc is
the synthesis.

## Decision

- **Single agent**: a hand-rolled tool-calling loop (Groq,
  `llama-3.3-70b-versatile`), no framework — built to establish a reliability
  baseline before adding any orchestration complexity.
- **Deterministic workflow**: plain Python for the two checks that have one
  unambiguous correct answer (date-range comparison, exclusion-list
  matching) — built specifically because the single agent's failures on
  exactly these checks (backwards date reasoning, hallucinated reference
  IDs) demanded a real comparison, not an assumption that "add an agent"
  was automatically the right tool.
- **Multi-agent (LangGraph)**: a 3-node pipeline — deterministic fact
  gathering, then a narrowly-scoped LLM discrepancy check, then an LLM
  summary — replacing the single agent's one do-everything loop.
- **Human-in-the-loop**: LangGraph's `interrupt()`/`Command(resume=...)`
  primitives, inserted between the discrepancy check and the summary, so a
  human can approve, reject, or edit findings before they reach a case
  worker.

## Alternatives considered

- **Trusting the single agent's tool-calling loop as the final design** —
  rejected outright. On a claim with a known, unambiguous correct answer
  (zero real discrepancies), 10 identical runs produced only 2 correct
  results, 7 false positives, and 1 crash — with two *recurring* failure
  patterns (backwards date comparison, a hallucinated fake policy ID used
  to justify a fabricated "mismatch"), not random noise.
- **Assuming multi-agent decomposition automatically fixes reliability** —
  tested directly, and it didn't, on the first two attempts. Splitting
  fact-gathering into plain code did eliminate the hallucinated-ID failure
  by construction (the LLM never re-types an ID it already has). But the
  narrowly-scoped discrepancy-checking LLM step still needed **two more**
  rounds of prompt debugging — first to stop padding the findings list with
  confirmations disguised as issues, then to correct a genuine,
  consistently-reproduced misunderstanding of standard insurance
  terminology (treating a claim's gross repair estimate as if the
  deductible should already be subtracted from it).
- **A dedicated cross-encoder / sentence-transformers approach** — not
  applicable to this phase, but the same lesson from Phase 1 (avoid heavy
  dependencies with no clear payoff) informed keeping the single agent
  framework-free.
- **Treating "deterministic beats agent" as a blanket conclusion** —
  explicitly rejected. The deterministic checker only wins because the date
  and exclusion checks are exactly the kind of task it's built for:
  structured data, one correct answer. It has no mechanism for the kind of
  judgment call the agent handled well in
  [phase-2-human-in-the-loop.md](./phase-2-human-in-the-loop.md) — noticing
  that an $800 repair estimate falls below a $1,000 deductible, something
  nothing in this project asked either system to check for.

## Why

- **Reliability had to be measured, not assumed.** Every claim in this
  phase's docs about agent behavior — the 2/10 baseline, the 3 rounds of
  multi-agent prompt debugging, the human-in-the-loop demo's captured
  override — came from actually running the identical task 10 times, or
  building a synthetic broken case, and counting outcomes. A single
  successful run (which is how each of these components first "worked" in
  early testing) would have hidden every one of these findings.
- **The task's own structure justified a hybrid, not a single answer.**
  Claim discrepancy checking has both mechanically verifiable rules (date
  ranges, exact exclusion matches) and genuinely open-ended judgment calls
  (is this "except" clause's carve-out satisfied here, does this cost
  pattern deserve a flag nothing was asked to check for). Forcing either a
  pure-agent or pure-code answer onto the whole task would have been wrong
  in one direction or the other.
- **Human review isn't a compliance checkbox here — the evidence demands
  it.** Even after 3 rounds of prompt tuning brought the multi-agent
  pipeline to 10/10 on its test claim, a harder, genuinely ambiguous case
  reproduced a subtler version of an earlier bug (an item labeled an
  "issue" that contradicts its own stated reasoning). That's not a
  hypothetical risk this phase is choosing to guard against out of caution
  — it's a failure mode this phase's own testing directly observed.

## What I'd change at real production scale

- **Test against harder, more ambiguous cases systematically**, not just
  the one clear-cut broken-claim pair and one hand-built ambiguous case
  used here. This phase's golden set for agent behavior is much thinner
  than Phase 1's 19-question retrieval golden set — building an equivalent
  here (a real set of claims spanning easy, hard, and adversarial cases) is
  exactly what Phase 5 formalizes, and this phase would benefit from it
  now, not just later.
- **A real reviewer interface**, not a script standing in for one. The
  interrupt/resume mechanism is genuinely LangGraph's real primitive for
  this; the "human" in every test here was still code making a decision.
- **Structured output guarantees**, not prompt-level JSON instructions.
  Both the single agent and early multi-agent versions occasionally
  produced malformed JSON or protocol-breaking tool-call syntax. Groq (and
  most providers) support constrained/structured output modes that would
  eliminate this whole failure category rather than relying on "please
  respond with only JSON" holding every time.
- **Extend the deterministic/agent hybrid**, rather than routing everything
  through an LLM by default. The pattern that worked here — deterministic
  code for anything with one unambiguous correct answer, LLM reasoning
  reserved for genuine judgment calls, human review as the backstop — is a
  design principle worth applying to every future check this system adds,
  not just the two built in this phase.
- **Revisit whether 3 rounds of prompt-tuning against one claim
  generalizes.** It was verified against the other 4 real claims and the
  synthetic broken cases, which is a real (if thin) check — but a
  production system would need this validated against a much larger and
  more varied claim set before trusting the tuned prompt's reliability
  claims at face value.

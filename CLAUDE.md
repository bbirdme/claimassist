# ClaimAssist — AI Solution Architecture Learning Project

## What this is
A self-directed learning project to build AI Solution Architect skills through one evolving
system, built in phases, over ~6-9 months at 1-2h/day. Each phase adds one architectural layer.
The code matters less than the written decision docs — the goal is to practice making and
defending architecture choices, not just to get something running.

**The system:** ClaimAssist — an AI copilot for a fictional regulated healthcare client that
helps case workers process insurance claims: look up a claim, retrieve relevant policy/medical
documents, flag discrepancies, summarize for human review.

## How Claude Code should work with me on this
- **I am learning, not delegating.** Don't just write full solutions when I ask "how do I do X."
  Explain the options, the trade-offs, and a recommended approach; write code with me or in small
  pieces I can follow, not a finished black box.
- **Push back on my architecture decisions.** If I pick a chunking strategy, vector DB, or agent
  pattern, ask me why before confirming it's reasonable. If my reasoning is weak, say so.
- **After each phase, help me write the decision doc** (see format below) rather than just
  leaving the reasoning implicit in code comments.
- **Flag when I'm cutting a corner that a real client project wouldn't allow** — e.g. skipping
  PII redaction "for now," hardcoding secrets, ignoring auth. Call it out even if it's fine for a
  learning project, so I know the difference between "shortcut" and "correct."
- Assume Python as the primary language unless a phase specifically calls for something else.

## Decision doc format (use this at the end of every phase)
Save each as `docs/phase-N-<name>.md`:
```
# Phase N: <topic>
## Decision
What I chose.
## Alternatives considered
What else was on the table.
## Why
Reasoning tied to constraints (corpus size, latency, cost, data sensitivity, client type).
## What I'd change at real production scale
Honest gaps between this toy version and a real deployment.
```

## Repo structure
```
claimassist/
  docs/                  # phase decision docs, architecture diagrams
  data/                  # synthetic claim forms, policy docs, medical notes (fake/generated data only)
  src/
    ingestion/           # chunking, embedding, indexing
    retrieval/           # hybrid search, reranking
    agents/              # agent definitions, tools, orchestration
    integrations/         # mock enterprise API, auth
    security/            # PII redaction, injection defenses, audit logging
    eval/                # golden dataset, LLM-as-judge, regression tests
    observability/       # tracing setup
  infra/                 # docker-compose for pgvector, mock services, etc.
  tests/
```

## Phase plan

### Phase 0 — LLM Fundamentals (Weeks 1-3)
- Call Claude, OpenAI, and one open-source model (via Ollama/Together) with the same prompts.
- Compare tokenization, latency, cost, context window behavior.
- Deliverable: `docs/phase-0-provider-comparison.md`

### Phase 1 — RAG Architecture (Weeks 4-10)
- Build the corpus (synthetic claim forms/policy docs — generate these, don't use real data).
- Try fixed-size vs semantic vs structural chunking.
- Try 2 embedding models. Stand up pgvector. Add hybrid search (vector + BM25). Add reranking.
- Deliverable: `docs/phase-1-rag-architecture.md`

### Phase 2 — Agent Architecture (Weeks 11-16)
- Single-agent version (tool use, structured output) for claim lookup + discrepancy check.
- Multi-agent version (LangGraph) of the same task. Compare against a code-native version.
- Add a human-in-the-loop approval step.
- Build one case where a deterministic workflow beats an agent — document why.
- Deliverable: `docs/phase-2-agent-architecture.md`

### Phase 3 — Integration Architecture (Weeks 17-20)
- Mock "enterprise" REST API (fake ERP/claims system) with OAuth2 client-credentials auth.
- Add an API gateway in front of the agent. Design (doc, not necessarily build) SSO and
  multi-tenant data isolation.
- Deliverable: `docs/phase-3-integration-architecture.md`

### Phase 4 — Security & Compliance Architecture (Weeks 21-24)
- PII detection/redaction on input and output.
- Deliberately attempt prompt injection against your own agent via a poisoned retrieved doc,
  then add defenses.
- Full audit logging of tool calls, retrievals, model calls.
- EU AI Act risk classification writeup for this system.
- Deliverable: `docs/phase-4-security-architecture.md`

### Phase 5 — Observability & Evaluation Architecture (Weeks 25-30)
- Add tracing (Langfuse or OpenTelemetry).
- Build a 20-50 example golden dataset. Implement LLM-as-judge scoring.
- Add a regression check for prompt/model changes.
- Deliverable: `docs/phase-5-eval-architecture.md`

### Phase 6 — Cost & Deployment Architecture (Weeks 31-36)
- Implement prompt caching, measure the delta.
- Design a model routing strategy (cheap model for simple tasks, frontier for complex).
- Try self-hosting an open model with vLLM, even briefly, to get real cost/latency numbers.
- Build a TCO comparison: pure API vs hybrid vs self-hosted.
- Deliverable: `docs/phase-6-cost-architecture.md`

### Phase 7 — Capstone (Weeks 37-40+)
- Combine everything into one architecture diagram and a full technical proposal (approach,
  architecture, timeline, team, risks, cost) as if pitching to a real client.
- Record a 15-minute presentation of it, twice: once as if to a CTO, once as if to a junior dev.
- Deliverable: `docs/phase-7-proposal.md` + architecture diagram.

## Constraints to respect throughout
- All data must be synthetic/generated — never use or reference real patient/claim data.
- Prefer boring, explainable choices over clever ones; the point is defensible architecture,
  not maximal sophistication.
- Every phase should end with something runnable AND something written. Code without the
  decision doc doesn't count as done.

## Current status
Phase: 0 complete (docs/phase-0-provider-comparison.md). Phase 1 (RAG Architecture) not started.
Last updated: 2026-07-21

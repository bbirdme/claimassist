# ClaimAssist

A self-directed learning project to build AI Solution Architect skills through one
evolving system, built in phases over ~6-9 months. Each phase adds one
architectural layer (RAG, agents, integration, security, observability, cost/
deployment) to the same fictional system, and ends with both working code and a
written decision doc defending the choices made.

**The system:** ClaimAssist is an AI copilot for a *fictional* regulated
healthcare client, helping case workers process insurance claims — look up a
claim, retrieve relevant policy/medical documents, flag discrepancies, and
summarize for human review. All data is synthetic; no real patient or claim
data is ever used.

The point of this project is the architecture reasoning, not the code. See
[`CLAUDE.md`](./CLAUDE.md) for the full phase plan and the working philosophy
behind it.

## Status

| Phase | Topic | Status | Decision doc |
|---|---|---|---|
| 0 | LLM Fundamentals | ✅ Done | [phase-0-provider-comparison.md](./docs/phase-0-provider-comparison.md) |
| 1 | RAG Architecture | Not started | — |
| 2 | Agent Architecture | Not started | — |
| 3 | Integration Architecture | Not started | — |
| 4 | Security & Compliance | Not started | — |
| 5 | Observability & Evaluation | Not started | — |
| 6 | Cost & Deployment | Not started | — |
| 7 | Capstone | Not started | — |

This table is updated at the end of every phase.

## Stack

- **Language:** Python 3.12
- **Package/env manager:** [uv](https://github.com/astral-sh/uv)
- **LLM providers used so far:**
  - [Google Gemini](https://aistudio.google.com) (`google-genai`) — hosted, free tier
  - [Groq](https://console.groq.com) (`groq`) — hosted, free tier, serves open-weight models
  - [Ollama](https://ollama.com) — fully local, open-weight models, no API key
- **Vector store:** [pgvector](https://github.com/pgvector/pgvector) (Postgres 17), via Docker
- Stack grows as later phases add LangGraph, Langfuse/OpenTelemetry, vLLM,
  etc. — see `CLAUDE.md` for the full plan.

## Setup

```bash
# install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# install dependencies
uv sync

# copy env template and fill in your own free-tier API keys
cp .env.example .env
```

Gemini and Groq both have genuine free tiers (no credit card required):
- Gemini key: [aistudio.google.com](https://aistudio.google.com) → "Get API key"
- Groq key: [console.groq.com](https://console.groq.com) → "API Keys"

For pgvector, start the local Postgres container:
```bash
cd infra && docker compose up -d
```

For the local model, install [Ollama](https://ollama.com/download) and pull a
small model:
```bash
ollama pull llama3.2:3b
```

## Repo structure

```
claimassist/
  docs/     # phase decision docs + supporting evidence (results, diagrams)
  data/     # synthetic claim forms, policy docs, medical notes (fake data only)
  src/      # ingestion, retrieval, agents, integrations, security, eval, observability
  infra/    # docker-compose for pgvector, mock services, etc.
  tests/
```

## Workflow

Each phase is built on its own branch (`phase-N-<name>`) and merged into `main`
via pull request once the code runs and the decision doc is written. `main`
always reflects the latest completed phase.

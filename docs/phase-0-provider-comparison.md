# Phase 0: LLM Provider Comparison

## What was tested

The original Phase 0 plan called for comparing Claude, OpenAI, and one open-source
model. That plan changed mid-phase for budget reasons (see **Why** below). What
actually got built and run:

**Providers:**
- **Gemini** (`gemini-flash-latest`) — hosted, proprietary, free tier via Google AI Studio
- **Groq** (`llama-3.3-70b-versatile`) — hosted, open-weight model, free tier
- **Ollama** (`llama3.2:3b`) — open-weight model, running fully locally, no network call

**Prompts (same 3 sent to all 3 providers):**
1. `factual_short` — *"What is subrogation in insurance?"* — a short factual question,
   baseline for tokenization and latency with no context load.
2. `claim_summary` — a synthetic ~200-word insurance claim narrative (fake claimant,
   fake policy, fake storm-damage story), asking for a 3-sentence summary — tests
   context handling and latency as input size grows.
3. `claim_extraction` — the same claim narrative, asking the model to return a JSON
   object with 5 specific fields (claimant name, policy number, date of loss,
   deductible, total repair cost) — tests structured output *without* using any
   provider's dedicated JSON mode or tool-calling API, and tests whether the
   extracted values are actually correct, not just well-formed.

**How the harness works** (`src/eval/phase0/`):
- `providers.py` — one function per provider (`call_ollama`, `call_groq`,
  `call_gemini`), each with an identical return shape: response text, prompt/
  completion token counts (as reported natively by that provider — this is the
  actual thing being compared, since each provider tokenizes differently),
  latency, and cost.
- Latency is measured with our own wall-clock timer (`time.monotonic()`) around
  each call, not each provider's self-reported duration field — those fields
  differ in what they include (queueing, network, etc.), so a provider's own
  number isn't a fair cross-provider comparison.
- `prompts.py` — the 3 test prompts and the synthetic claim narrative they share.
- `run_comparison.py` — runs all 3 prompts against all 3 providers (9 calls total),
  prints a summary line per call, and writes full raw results to
  `docs/phase-0-results.json` as the evidence backing this doc.
- For `claim_extraction`, the harness also strips markdown code fences and attempts
  `json.loads()` on the response, recording whether it parsed as valid JSON at all.

## Results

See [phase-0-results-explained.md](./phase-0-results-explained.md) for a
deeper walkthrough of these numbers — an actual token-split example, why
prompt tokens vs. completion tokens diverge for different reasons, and real
dollar-cost math using current provider pricing applied to our measured token
counts. See
[phase-0-prompt-vs-completion-tokens.md](./phase-0-prompt-vs-completion-tokens.md)
for a follow-up correction on what actually drives prompt-token differences
(vocabulary vs. hidden chat-template overhead).

| Prompt | Provider | Prompt tokens | Completion tokens | Latency |
|---|---|---|---|---|
| factual_short | ollama | 33 | 417 | 28.09s |
| factual_short | groq | 43 | 433 | 1.40s |
| factual_short | gemini | 8 | 931 | 8.85s |
| claim_summary | ollama | 375 | 130 | 11.65s |
| claim_summary | groq | 385 | 140 | 0.82s |
| claim_summary | gemini | 360 | 134 | 4.67s |
| claim_extraction | ollama | 395 | 61 | 8.47s |
| claim_extraction | groq | 405 | 73 | 0.43s |
| claim_extraction | gemini | 385 | 91 | 4.10s |

**Extraction correctness** (ground truth total repair cost = $8,450 + $1,200 = **$9,650**):

| Provider | Extracted total | Correct? |
|---|---|---|
| Ollama (llama3.2:3b, local) | $10,550 | ✗ |
| Groq (llama-3.3-70b, hosted) | $9,450 | ✗ |
| Gemini (flash) | $9,650 | ✓ |

All three names, dates, and other fields were extracted correctly and as valid
JSON by all three providers. Only the arithmetic (summing two numbers stated
plainly in the source text) tripped up both open-weight models.

**Key observations:**
- **Tokenization varies a lot for identical input.** The same 5-word question
  produced 8 tokens on Gemini's tokenizer vs. 33 on Ollama's vs. 43 on Groq's —
  nearly a 5x spread. Token counts across providers are not directly comparable
  without knowing each one's tokenizer.
- **Hosted inference chips (Groq) are dramatically faster than local CPU
  inference (Ollama)** — roughly 10-20x in this test — which matters if latency
  is a product requirement.
- **"Valid JSON" is not the same as "correct."** All three models followed the
  JSON-shape instruction with no explicit JSON mode. Only Gemini got the actual
  values right. A discrepancy-flagging agent (Phase 2) that trusted an
  open-weight model's raw extraction here would silently propagate a wrong
  dollar figure.
- **Sample size is 1 per cell.** This is a single run per prompt/provider pair —
  enough to see qualitative differences, not enough to draw statistically
  reliable conclusions about latency variance or extraction accuracy rates.

## Decision

Ran the comparison with **Gemini + Groq + Ollama** instead of the originally
planned **Claude + OpenAI + one open-source model**.

## Alternatives considered

- **Keep Claude/OpenAI in scope, accept a tiny real cost.** Rejected — the
  constraint going in was genuinely $0 spend, not "as cheap as possible."
- **Use a different second hosted proprietary API** (e.g. Mistral's free tier).
  Not tried — Gemini was sufficient to fill that role and is arguably the more
  recognizable comparison point.
- **Skip the local model entirely and use two hosted free APIs (Gemini + Groq
  only).** Considered and rejected in favor of including Ollama, since a fully
  local model is a materially different deployment shape (no network, no
  vendor, no per-request cost at any volume) and previews the self-hosting
  question Phase 6 asks explicitly.

## Why

The plan assumed access to Claude and OpenAI's APIs. Neither has a perpetual
free tier — any call, however small, costs real money and (for a fresh key)
often needs a card on file. The actual constraint was zero spend, not "low
cost," which removed both from the comparison entirely rather than just making
them the "expensive" line item.

Gemini and Groq both have genuine free tiers with no billing setup required,
so they preserve the spirit of "compare hosted proprietary vs. hosted
open-weight" behavior. Ollama adds a third, qualitatively different axis —
self-hosted with zero per-request cost and no data leaving the machine — which
the original two-hosted-API plan wouldn't have surfaced at all.

One consequence worth naming directly: with all three providers free, the
**cost axis of this comparison is currently moot** — there's no real cost data
to compare, only $0 vs $0 vs $0. The phase's cost-comparison goal is deferred,
not actually met.

## What I'd change at real production scale

- **Include Claude and/or OpenAI.** A real client engagement would just pay for
  API access; a production provider comparison without the two leading
  proprietary APIs is incomplete. This gap is a direct, known artifact of the
  self-imposed $0 constraint, not a real architectural conclusion.
- **Get real cost data.** Re-run with paid tiers and record actual per-request
  and per-token pricing, not $0 placeholders — the current numbers say nothing
  about production cost trade-offs.
- **Increase sample size.** Run each prompt several times per provider and
  report latency distributions (p50/p95), not single data points — one call
  per cell can't distinguish a fluke from a real pattern.
- **Use each provider's actual structured-output / tool-calling mode** instead
  of asking for JSON in plain prose. This test deliberately used raw prompting
  to see baseline instruction-following, but production extraction should use
  the reliability guarantees those modes provide.
- **Check free-tier data-use terms before reusing this setup with anything
  sensitive.** Free tiers on hosted APIs commonly reserve rights to use
  submitted prompts for training or human review — a materially different
  posture than a paid tier. Even with synthetic data here, a regulated-client
  system should be deliberate about which tier and which data-handling terms
  apply, and that decision doesn't disappear just because Phase 0 used
  placeholder data.
- **Test extraction accuracy on more than one example.** One narrative isn't
  enough to claim "open-weight models are worse at arithmetic-in-extraction" —
  that would need a small golden set (this is exactly what Phase 5 builds).

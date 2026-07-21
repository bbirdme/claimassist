# Phase 0: Results Explained

A deeper walkthrough of what the numbers in
[phase-0-provider-comparison.md](./phase-0-provider-comparison.md) actually
mean, with the real token counts, latency, and cost math behind them. Raw data
is in [phase-0-results.json](./phase-0-results.json).

## 1. What a "token" physically is

A token is a chunk of text a model's vocabulary maps to a single ID — not a
word, not a character. Here's an actual tokenizer split of our test sentence
(using a standard open tokenizer as a stand-in to illustrate the mechanism —
not the literal tokenizer any of our 3 providers used internally, each has its
own):

```
"What is subrogation in insurance?"
→ ['What', ' is', ' sub', 'rog', 'ation', ' in', ' insurance', '?']
```

Common words (`What`, `is`, `in`, `insurance`) each stay as one token.
"Subrogation" — a rarer, domain-specific word — splits into 3 pieces (`sub` +
`rog` + `ation`) because it wasn't common enough in that tokenizer's training
corpus to earn its own vocabulary slot. This is the entire mechanism behind why
token counts diverge across providers: each one built its vocabulary from a
different corpus, so the same word can be 1 token in one vocabulary and 3+ in
another.

## 2. The actual token counts measured

| Prompt | Provider | Prompt tokens | Completion tokens |
|---|---|---|---|
| factual_short | ollama (Llama 3.2 tokenizer) | 33 | 417 |
| factual_short | groq (Llama 3.3 tokenizer) | 43 | 433 |
| factual_short | gemini | 8 | 931 |
| claim_summary | ollama | 375 | 130 |
| claim_summary | groq | 385 | 140 |
| claim_summary | gemini | 360 | 134 |
| claim_extraction | ollama | 395 | 61 |
| claim_extraction | groq | 405 | 73 |
| claim_extraction | gemini | 385 | 91 |

Two different phenomena are hiding in this table:

- **Prompt tokens** (same input text, different count): partly tokenizer
  vocabulary, but — as a follow-up test revealed — mostly something else
  entirely. See
  [phase-0-prompt-vs-completion-tokens.md](./phase-0-prompt-vs-completion-tokens.md)
  for the corrected, verified explanation; the original claim here (that this
  was "pure tokenizer vocabulary difference") turned out to be substantially
  wrong.
- **Completion tokens** (same question, wildly different output length): this
  is **not** tokenization, it's the model choosing to write more or less. On
  `factual_short`, Gemini wrote a 931-token answer (with headers, a worked
  example, and a "waiver of subrogation" tangent) vs. Groq's 433-token answer —
  more than 2x the length for the same question. That's a verbosity /
  instruction-following difference, not a vocabulary difference, and the two
  causes should be kept separate when reasoning about "why did this cost more."

## 3. Latency — why the gap is so large

Real wall-clock seconds per call (measured with our own timer, not each
provider's self-reported duration field — see methodology note in the main
doc):

| Provider | factual_short | claim_summary | claim_extraction |
|---|---|---|---|
| ollama (local CPU) | 28.09s | 11.65s | 8.47s |
| groq (custom chips) | 1.40s | 0.82s | 0.43s |
| gemini (hosted) | 8.85s | 4.67s | 4.10s |

Groq is consistently fastest by a wide margin — that's the entire premise of
Groq as a company: purpose-built chips (LPUs) for token generation, not
general-purpose GPUs. Ollama is slowest because this machine runs inference on
CPU with no dedicated AI accelerator — a GPU would change this substantially.
Gemini sits in between: real GPU/TPU infrastructure, but also network
round-trip time to Google's servers, which local Ollama doesn't pay.

## 4. Cost — real dollar figures using current published pricing

Actual spend on this test was $0 across all three providers. To make "cost"
concrete anyway, here's what the same 9 calls would cost applying each
provider's *actual current published pricing* to the *actual token counts we
measured*:

- **Groq** (`llama-3.3-70b-versatile`): $0.59 / million input tokens, $0.79 /
  million output tokens
- **Gemini** (current Flash tier): $1.50 / million input tokens, $9.00 /
  million output tokens
- **Ollama**: $0 — no vendor, just local electricity/hardware

| Provider | Total across 3 calls |
|---|---|
| Groq | **$0.0010** (~0.1¢) |
| Gemini | **$0.0115** (~1.15¢) |

Gemini's hypothetical cost is **~11x higher** than Groq's for the identical 3
prompts, driven by two compounding factors: Gemini's output pricing is itself
~11x more expensive per token ($9.00 vs $0.79/M), *and* Gemini's answers were
more verbose. The single `factual_short` call alone would have cost $0.0084 on
Gemini — more than Groq's entire 3-call total.

Scaled to make it tangible: if a case worker asked just the short factual
question 1,000 times a day, that's roughly **$1/day on Groq vs. ~$11.50/day on
Gemini** — a real, non-trivial operating-cost difference at production volume,
from model choice alone.

**Caveat:** `gemini-flash-latest` is an alias that may route to a specific
dated model version. Which exact version answered these calls vs. which one
the live pricing page describes cannot be fully reconciled — treat this as a
good-faith estimate, not an exact bill.

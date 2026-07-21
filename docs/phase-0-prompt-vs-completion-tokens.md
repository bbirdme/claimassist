# Phase 0: Prompt Tokens vs. Completion Tokens, in Practice

Follow-up to [phase-0-results-explained.md](./phase-0-results-explained.md),
prompted by a specific question: *does a bigger vocabulary / more knowledgeable
model need fewer prompt tokens?* Short answer: partly, but that question
conflates two different things, and the first explanation of our own data was
wrong about which effect actually mattered. This doc corrects it with a
verified follow-up test.

## The claim that turned out to be wrong

The original results doc said the prompt-token gap (Ollama 33, Groq 43,
Gemini 8, all for the identical sentence "What is subrogation in insurance?")
was "pure tokenizer vocabulary difference." That was tested and found
substantially incomplete.

## The test

Ollama runs locally, so its API can be told to skip all chat formatting and
tokenize raw text directly (`"raw": true`). Groq and Gemini are hosted APIs
with no equivalent raw mode — this asymmetry matters and is addressed below.

| Call | prompt_tokens |
|---|---|
| Ollama, `/api/generate`, default (chat template applied) | 33 |
| Ollama, `/api/chat`, same message structure Groq/Gemini use | 33 |
| Ollama, `/api/generate`, `raw: true` (**zero templating, just the tokenizer**) | **9** |
| Gemini (single-turn `generate_content`) | 8 |
| Groq (chat-completions API — no raw mode exists to test) | 43 |

The finding: with all chat-template formatting stripped away, Llama 3.2's
*raw tokenizer* produces 9 tokens for this sentence — almost identical to
Gemini's reported 8. The other 24 tokens in the original "33" (73% of it) were
not vocabulary at all — they were **chat-template scaffolding**: role tags and
special control tokens (things like `<|begin_of_text|>`,
`<|start_header_id|>user<|end_header_id|>`, `<|eot_id|>`) that Ollama silently
wraps around your text before tokenizing it, by default, whether you call the
"completion" endpoint or the "chat" endpoint.

**Groq's 43 could not be fully dissected** the same way — its SDK only exposes
a chat-completions method, no raw/legacy completion endpoint, so its 43
includes an unknown mix of tokenizer vocabulary and whatever system/role
formatting Groq's API applies internally. Any claim about "Groq's tokenizer is
less efficient than Gemini's" is not actually verified — it's confounded with
unmeasurable template overhead, exactly like Ollama's number was until this
test.

## So: does bigger vocabulary/knowledge mean fewer prompt tokens?

Two separate things were bundled into that question — worth pulling apart:

**Vocabulary size** is a real, measurable lever, but it's a tokenizer design
choice made once, independently of the model — not a byproduct of the model
"knowing more." Concrete proof: Meta's entire Llama 3 family (3, 3.1, 3.2,
3.3 — spanning 1B to 405B parameters) shares a single, identical tokenizer. A
1B model and a 405B model tokenize the exact same sentence into the exact same
number of tokens, despite the 405B model being vastly more capable. Vocabulary
size and model capability are decided independently and don't cause each
other, even though frontier labs often invest in both at once, creating a
loose correlation that's easy to mistake for causation.

Once vocabulary is isolated from template overhead (Ollama raw=9, Gemini=8),
the *actual* vocabulary-driven gap in this test was small — nowhere near the
originally reported 8-vs-33 spread. Most of what looked like "a smarter model
needs fewer tokens" was really "this API added more invisible formatting
before counting."

**"Knowledge"** (facts, reasoning ability, instruction-following) is a
property of training, not of the tokenizer, and has no direct mechanical
relationship to prompt token count at all.

## What actually determines completion tokens, then?

Not vocabulary, not knowledge either — it's the model's learned response
style (an instruction-tuning/RLHF choice about how verbose to be by default),
which is orthogonal to both. Our data: for the identical question, Gemini
wrote 931 completion tokens, Groq 433, Ollama 417 — a stylistic choice about
how much to write, not a difference in what each model knows or how its
vocabulary is built.

## Practical takeaway for ClaimAssist

Chat-template overhead is invisible unless you deliberately test for it, and
it varies by provider and even by which endpoint you call on the same
provider. That means "prompt tokens" reported by an API is not a clean proxy
for "how efficiently does this model represent text" — it's a proxy for "the
whole request pipeline, including formatting most SDKs never expose." For any
future phase that cares about real token/cost budgets (Phase 5's evaluation
work, Phase 6's cost architecture), the reliable approach is to measure actual
production request/response payloads directly rather than reason from a
single provider's self-reported count.

## Methodology note

This test was only possible to fully verify on Ollama because it runs locally
and exposes a `raw` flag. Groq and Gemini are hosted, closed pipelines with no
equivalent — their prompt-token numbers should be treated as "tokenizer +
unknown template overhead, bundled together," not as a clean vocabulary
measurement.

import json
import re
import time

from groq import RateLimitError

from src.integrations.llm_providers import call_groq

RERANK_PROMPT = """You are a relevance-ranking assistant for an insurance \
claims retrieval system. Given a QUERY and a list of candidate PASSAGES, \
score how relevant each passage is to answering the query, on a scale of \
0-10 (10 = directly answers the query, 0 = completely irrelevant).

Return ONLY a JSON array of objects with this exact shape, one entry per \
passage, in the same order given:
[{{"index": 0, "score": <int>}}, {{"index": 1, "score": <int>}}, ...]

QUERY: {query}

PASSAGES:
{passages}
"""


def _format_passages(candidates: list[tuple[str, str, float]]) -> str:
    return "\n\n".join(
        f"[{i}] (doc: {doc_id})\n{text}" for i, (doc_id, text, _score) in enumerate(candidates)
    )


def _parse_scores(response_text: str) -> dict[int, int]:
    cleaned = re.sub(r"^```(json)?|```$", "", response_text.strip(), flags=re.MULTILINE).strip()
    parsed = json.loads(cleaned)
    return {item["index"]: item["score"] for item in parsed}


def _call_groq_with_retry(prompt: str, max_retries: int = 5) -> dict:
    """Switched the reranker from Gemini to Groq: gemini-3.6-flash's free
    tier caps generateContent at 20 requests/DAY (not per-minute), too tight
    for a 24-query test set in one session. Groq had no such daily cap in
    Phase 0's testing, so it's a better fit for this many calls."""
    for attempt in range(max_retries):
        try:
            return call_groq(prompt)
        except RateLimitError:
            if attempt < max_retries - 1:
                print(f"  rate limited, waiting 15s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(15)
            else:
                raise


def llm_rerank(query: str, candidates: list[tuple[str, str, float]], top_k: int = 3):
    """Listwise LLM reranking: one call sees all candidates together (rather
    than scoring each independently), so it can judge relevance relative to
    the other candidates, not just in isolation."""
    prompt = RERANK_PROMPT.format(query=query, passages=_format_passages(candidates))
    result = _call_groq_with_retry(prompt)
    scores = _parse_scores(result["response_text"])

    scored = [
        (doc_id, text, scores.get(i, 0)) for i, (doc_id, text, _orig_score) in enumerate(candidates)
    ]
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_k]

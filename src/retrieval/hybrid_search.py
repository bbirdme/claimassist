from rank_bm25 import BM25Okapi

from src.retrieval.bm25_search import bm25_search


def reciprocal_rank_fusion(*ranked_lists: list[tuple[str, str, float]], k: int = 60):
    """Combine ranked lists of (doc_id, chunk_text, score) via Reciprocal
    Rank Fusion: an item's fused score is the sum of 1/(k + rank) across
    every list it appears in. RRF only looks at rank *position*, not the raw
    score - deliberately, since BM25 scores are unbounded and corpus-size
    dependent while cosine similarity is bounded to [0, 1], so a naive
    weighted sum of the two raw scores would need careful, corpus-specific
    normalization. RRF sidesteps that entirely."""
    fused_scores: dict[tuple[str, str], float] = {}

    for ranked_list in ranked_lists:
        for rank, (doc_id, text, _score) in enumerate(ranked_list):
            key = (doc_id, text)
            fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (k + rank + 1)

    ranked = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
    return [(doc_id, text, score) for (doc_id, text), score in ranked]


def hybrid_search(
    vector_results: list[tuple[str, str, float]],
    bm25: BM25Okapi,
    bm25_chunks: list[tuple[str, str]],
    query: str,
    top_k: int = 3,
    candidate_k: int = 10,
):
    bm25_results = bm25_search(bm25, bm25_chunks, query, top_k=candidate_k)
    fused = reciprocal_rank_fusion(vector_results, bm25_results)
    return fused[:top_k]

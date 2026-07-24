from dotenv import load_dotenv

from src.eval.golden_set import GOLDEN_SET
from src.eval.hybrid_search_eval import IDENTIFIER_QUERIES
from src.integrations.embedding_providers import embed_gemini
from src.retrieval.vector_store import get_connection, query_similar
from src.retrieval.bm25_search import build_bm25_corpus
from src.retrieval.hybrid_search import hybrid_search
from src.retrieval.llm_rerank import llm_rerank


def run(questions: list[dict], label: str, conn, bm25, bm25_chunks, top_k: int = 3, candidate_k: int = 10):
    hybrid_hits, rerank_hits = 0, 0
    rows = []

    for q in questions:
        query_text = q.get("question") or q["query"]
        source_docs = set(q["source_docs"])

        query_embedding = embed_gemini(query_text, output_dimensionality=1536)
        vector_results = query_similar(conn, query_embedding, top_k=candidate_k)

        hybrid_candidates = hybrid_search(vector_results, bm25, bm25_chunks, query_text, top_k=candidate_k, candidate_k=candidate_k)
        hybrid_top = [d for d, _, _ in hybrid_candidates[:top_k]]

        reranked = llm_rerank(query_text, hybrid_candidates, top_k=top_k)
        rerank_top = [d for d, _, _ in reranked]

        h_hit = bool(set(hybrid_top) & source_docs)
        r_hit = bool(set(rerank_top) & source_docs)
        hybrid_hits += h_hit
        rerank_hits += r_hit

        rows.append((query_text, h_hit, r_hit, hybrid_top, rerank_top))

    n = len(questions)
    print(f"\n=== {label} (n={n}) ===")
    print(f"hybrid only        : {hybrid_hits}/{n} ({hybrid_hits/n:.0%})")
    print(f"hybrid + LLM rerank: {rerank_hits}/{n} ({rerank_hits/n:.0%})\n")

    for query_text, h, r, htop, rtop in rows:
        if h != r:
            print(f"  {query_text!r}  <-- DIFFERS")
            print(f"    hybrid only : {'HIT' if h else 'miss'} {htop}")
            print(f"    with rerank : {'HIT' if r else 'miss'} {rtop}")


if __name__ == "__main__":
    load_dotenv()
    conn = get_connection()
    bm25, bm25_chunks = build_bm25_corpus()

    run(GOLDEN_SET, "Golden set", conn, bm25, bm25_chunks)
    run(IDENTIFIER_QUERIES, "Identifier lookup queries", conn, bm25, bm25_chunks)

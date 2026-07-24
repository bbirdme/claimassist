from dotenv import load_dotenv

from src.eval.golden_set import GOLDEN_SET
from src.integrations.embedding_providers import embed_gemini
from src.retrieval.vector_store import get_connection, query_similar
from src.retrieval.bm25_search import build_bm25_corpus, bm25_search
from src.retrieval.hybrid_search import hybrid_search

# Bare document identifiers - a query that's just an ID has no semantic
# content for an embedding to work with beyond the literal characters, which
# is exactly the case BM25's exact term matching is supposed to be strong at
# and dense embeddings are sometimes weaker at.
IDENTIFIER_QUERIES = [
    {"query": "HO-88213-4", "source_docs": ["HO-88213-4"]},
    {"query": "CLM-2026-0412", "source_docs": ["CLM-2026-0412"]},
    {"query": "MED-0603-A", "source_docs": ["MED-0603-A"]},
    {"query": "AU-2298-3", "source_docs": ["AU-2298-3"]},
    {"query": "HI-6614-2", "source_docs": ["HI-6614-2"]},
]


def run_comparison(questions: list[dict], label: str, conn, bm25, bm25_chunks, top_k: int = 3):
    vector_hits, bm25_hits, hybrid_hits = 0, 0, 0
    rows = []

    for q in questions:
        query_text = q.get("question") or q["query"]
        source_docs = set(q["source_docs"])

        query_embedding = embed_gemini(query_text, output_dimensionality=1536)
        vector_results = query_similar(conn, query_embedding, top_k=10)

        bm25_results = bm25_search(bm25, bm25_chunks, query_text, top_k=top_k)
        hybrid_results = hybrid_search(vector_results, bm25, bm25_chunks, query_text, top_k=top_k)

        vector_top = [d for d, _, _ in vector_results[:top_k]]
        bm25_top = [d for d, _, _ in bm25_results]
        hybrid_top = [d for d, _, _ in hybrid_results]

        v_hit = bool(set(vector_top) & source_docs)
        b_hit = bool(set(bm25_top) & source_docs)
        h_hit = bool(set(hybrid_top) & source_docs)

        vector_hits += v_hit
        bm25_hits += b_hit
        hybrid_hits += h_hit

        rows.append((query_text, v_hit, b_hit, h_hit, vector_top, bm25_top, hybrid_top))

    n = len(questions)
    print(f"\n=== {label} (n={n}) ===")
    print(f"vector-only : {vector_hits}/{n} ({vector_hits/n:.0%})")
    print(f"bm25-only   : {bm25_hits}/{n} ({bm25_hits/n:.0%})")
    print(f"hybrid (RRF): {hybrid_hits}/{n} ({hybrid_hits/n:.0%})\n")

    for query_text, v, b, h, vtop, btop, htop in rows:
        if not (v and b and h):
            print(f"  {query_text!r}")
            print(f"    vector={'HIT' if v else 'miss'} {vtop}")
            print(f"    bm25  ={'HIT' if b else 'miss'} {btop}")
            print(f"    hybrid={'HIT' if h else 'miss'} {htop}")


if __name__ == "__main__":
    load_dotenv()
    conn = get_connection()
    bm25, bm25_chunks = build_bm25_corpus()

    run_comparison(GOLDEN_SET, "Golden set (semantic/factual questions)", conn, bm25, bm25_chunks)
    run_comparison(IDENTIFIER_QUERIES, "Identifier lookup queries", conn, bm25, bm25_chunks)

from dotenv import load_dotenv

from src.eval.golden_set import GOLDEN_SET
from src.integrations.embedding_providers import embed_gemini
from src.retrieval.vector_store import get_connection, query_similar


def evaluate(conn, top_k: int = 3):
    results = []
    for q in GOLDEN_SET:
        q_embedding = embed_gemini(q["question"], output_dimensionality=1536)
        rows = query_similar(conn, q_embedding, top_k=top_k)
        retrieved_doc_ids = [doc_id for doc_id, _, _ in rows]
        hit = bool(set(retrieved_doc_ids) & set(q["source_docs"]))
        results.append({"id": q["id"], "hit": hit, "retrieved": retrieved_doc_ids})

    hit_rate = sum(r["hit"] for r in results) / len(results)
    return hit_rate, results


if __name__ == "__main__":
    load_dotenv()
    conn = get_connection()

    hit_rate, results = evaluate(conn)
    print(f"pgvector (Gemini, 1536-dim, HNSW): hit rate {hit_rate:.1%}\n")

    for r in results:
        print(f"{r['id']}: {'HIT' if r['hit'] else 'miss'} ({r['retrieved']})")

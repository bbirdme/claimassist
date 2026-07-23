import numpy as np

from src.ingestion.load_corpus import load_corpus
from src.ingestion.chunking.structural import structural_chunk
from src.eval.golden_set import GOLDEN_SET
from src.integrations.embedding_providers import embed_ollama, embed_gemini


def _cosine(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


def build_chunks() -> list[tuple[str, str]]:
    """(doc_id, chunk_text) pairs for the whole corpus, using structural
    chunking - the strategy that came out ahead in the qualitative
    comparison."""
    chunks = []
    for doc in load_corpus():
        for chunk_text in structural_chunk(doc.text, doc.doc_type):
            chunks.append((doc.doc_id, chunk_text))
    return chunks


def evaluate(embed_fn, chunks: list[tuple[str, str]], top_k: int = 3):
    chunk_embeddings = [(doc_id, text, embed_fn(text)) for doc_id, text in chunks]

    results = []
    for q in GOLDEN_SET:
        q_embedding = embed_fn(q["question"])
        scored = sorted(chunk_embeddings, key=lambda c: _cosine(c[2], q_embedding), reverse=True)
        top = scored[:top_k]
        top_doc_ids = [doc_id for doc_id, _, _ in top]
        hit = bool(set(top_doc_ids) & set(q["source_docs"]))
        results.append({"id": q["id"], "hit": hit, "retrieved": top_doc_ids})

    hit_rate = sum(r["hit"] for r in results) / len(results)
    return hit_rate, results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    chunks = build_chunks()
    print(f"{len(chunks)} chunks total across {len(load_corpus())} documents\n")

    print("=== Ollama (nomic-embed-text, 768-dim) ===")
    ollama_rate, ollama_results = evaluate(embed_ollama, chunks)
    print(f"Hit rate: {ollama_rate:.1%}\n")

    print("=== Gemini (gemini-embedding-001, 3072-dim) ===")
    gemini_rate, gemini_results = evaluate(embed_gemini, chunks)
    print(f"Hit rate: {gemini_rate:.1%}\n")

    print("=== Per-question comparison ===")
    for o, g in zip(ollama_results, gemini_results):
        marker = "  <-- DIFFERS" if o["hit"] != g["hit"] else ""
        print(
            f"{o['id']}: ollama={'HIT' if o['hit'] else 'miss'} "
            f"({o['retrieved']}) gemini={'HIT' if g['hit'] else 'miss'} "
            f"({g['retrieved']}){marker}"
        )

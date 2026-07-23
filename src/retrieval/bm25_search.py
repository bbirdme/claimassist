import re

from rank_bm25 import BM25Okapi

from src.ingestion.load_corpus import load_corpus
from src.ingestion.chunking.structural import structural_chunk


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def build_bm25_corpus() -> tuple[BM25Okapi, list[tuple[str, str]]]:
    """Returns (bm25_index, chunks), where chunks is (doc_id, chunk_text)
    pairs in the same order the index was built from - same structural
    chunking used for the pgvector index, so results are directly comparable."""
    chunks = []
    for doc in load_corpus():
        for chunk_text in structural_chunk(doc.text, doc.doc_type):
            chunks.append((doc.doc_id, chunk_text))

    tokenized = [_tokenize(text) for _, text in chunks]
    bm25 = BM25Okapi(tokenized)
    return bm25, chunks


def bm25_search(bm25: BM25Okapi, chunks: list[tuple[str, str]], query: str, top_k: int = 3):
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [(doc_id, text, float(score)) for (doc_id, text), score in ranked[:top_k]]

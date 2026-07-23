from src.ingestion.load_corpus import load_corpus
from src.ingestion.chunking.fixed_size import fixed_size_chunk
from src.ingestion.chunking.structural import structural_chunk
from src.ingestion.chunking.semantic import semantic_chunk


def show(doc_id: str):
    docs = {d.doc_id: d for d in load_corpus()}
    doc = docs[doc_id]

    fixed = fixed_size_chunk(doc.text, chunk_size=500, overlap=50)
    structural = structural_chunk(doc.text, doc.doc_type)
    semantic = semantic_chunk(doc.text)

    print(f"=== {doc_id} ({doc.doc_type}, {len(doc.text)} chars) ===\n")

    print(f"--- fixed-size: {len(fixed)} chunks ---")
    for i, c in enumerate(fixed):
        print(f"[{i}] ({len(c)} chars) {c[:120]!r}")

    print(f"\n--- structural: {len(structural)} chunks ---")
    for i, c in enumerate(structural):
        print(f"[{i}] ({len(c)} chars) {c[:120]!r}")

    print(f"\n--- semantic: {len(semantic)} chunks ---")
    for i, c in enumerate(semantic):
        print(f"[{i}] ({len(c)} chars) {c[:120]!r}")
    print()


if __name__ == "__main__":
    show("HO-88213-4")
    show("CLM-2026-0412")

import time

from dotenv import load_dotenv
from google.genai.errors import ClientError

from src.ingestion.load_corpus import load_corpus
from src.ingestion.chunking.structural import structural_chunk
from src.integrations.embedding_providers import embed_gemini
from src.retrieval.vector_store import get_connection, create_schema, clear_chunks, insert_chunk


def embed_with_retry(text: str, output_dimensionality: int, max_retries: int = 5) -> list[float]:
    """Gemini's free tier allows 100 embedding requests/minute - a 118-chunk
    corpus can exceed that within one indexing run. Back off and retry
    rather than let a rate limit crash a one-time batch job."""
    for attempt in range(max_retries):
        try:
            return embed_gemini(text, output_dimensionality=output_dimensionality)
        except ClientError as e:
            if e.code == 429 and attempt < max_retries - 1:
                print(f"  rate limited, waiting 60s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(60)
            else:
                raise


def main():
    load_dotenv()
    conn = get_connection()
    create_schema(conn)
    clear_chunks(conn)

    count = 0
    for doc in load_corpus():
        for chunk_text in structural_chunk(doc.text, doc.doc_type):
            embedding = embed_with_retry(chunk_text, output_dimensionality=1536)
            insert_chunk(conn, doc.doc_id, doc.doc_type, chunk_text, embedding)
            count += 1

    conn.commit()
    print(f"Inserted {count} chunks into pgvector")


if __name__ == "__main__":
    main()

import os

import psycopg
from pgvector.psycopg import register_vector

EMBEDDING_DIM = 1536  # gemini-embedding-001, truncated from its default 3072
                       # dims via output_dimensionality - pgvector's HNSW
                       # index has a hard 2000-dim limit, so the full-size
                       # embedding from the Phase 1 comparison can't be
                       # indexed directly (see docs/phase-1-pgvector.md)


def get_connection() -> psycopg.Connection:
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)
    return conn


def create_schema(conn: psycopg.Connection):
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            doc_id TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector({EMBEDDING_DIM}) NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS chunks_embedding_idx
        ON chunks USING hnsw (embedding vector_cosine_ops)
    """)
    conn.commit()


def clear_chunks(conn: psycopg.Connection):
    conn.execute("TRUNCATE chunks")
    conn.commit()


def insert_chunk(conn: psycopg.Connection, doc_id: str, doc_type: str, chunk_text: str, embedding: list[float]):
    conn.execute(
        "INSERT INTO chunks (doc_id, doc_type, chunk_text, embedding) VALUES (%s, %s, %s, %s)",
        (doc_id, doc_type, chunk_text, embedding),
    )


def query_similar(conn: psycopg.Connection, query_embedding: list[float], top_k: int = 3):
    """Returns (doc_id, chunk_text, similarity) ordered by cosine similarity,
    most similar first. pgvector's <=> operator is cosine *distance*
    (1 - similarity), so ORDER BY ... <=> ASC gives closest first."""
    rows = conn.execute(
        """
        SELECT doc_id, chunk_text, 1 - (embedding <=> %s::vector) AS similarity
        FROM chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_embedding, query_embedding, top_k),
    ).fetchall()
    return rows

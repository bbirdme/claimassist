import re

import numpy as np

from src.integrations.embedding_providers import embed_ollama


_ABBREVIATIONS = {"Mr.", "Mrs.", "Ms.", "Dr.", "Jr.", "Sr.", "vs.", "etc.", "e.g.", "i.e.", "Inc.", "Ltd.", "No."}


def _split_sentences(text: str) -> list[str]:
    """Crude sentence splitter - adequate for grouping, not a real NLP
    sentence boundary detector. Merges back fragments that end in a common
    abbreviation (e.g. splitting "Mr." from "Whitfield" as if that period
    ended a sentence), since naive period-based splitting breaks on those by
    default; a real NLP tokenizer (spaCy, etc.) would handle this more
    generally, but that's more than this phase needs."""
    flattened = text.replace("\n", " ")
    raw_parts = re.split(r"(?<=[.!?])\s+", flattened)

    sentences = []
    buffer = ""
    for part in raw_parts:
        buffer = f"{buffer} {part}".strip() if buffer else part
        if any(buffer.endswith(abbr) for abbr in _ABBREVIATIONS):
            continue
        sentences.append(buffer)
        buffer = ""
    if buffer:
        sentences.append(buffer)

    return [s.strip() for s in sentences if s.strip()]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


def semantic_chunk(text: str, similarity_threshold: float = 0.5, embed_fn=embed_ollama) -> list[str]:
    """Group consecutive sentences together as long as each one is similar
    enough to the previous one; start a new chunk when similarity drops
    below the threshold, i.e. when the topic shifts. Unlike fixed-size and
    structural chunking, this doesn't need to know anything about document
    type or layout - it works the same way on a policy document, a claim
    narrative, or a medical note, at the cost of one embedding call per
    sentence."""
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return sentences

    embeddings = [embed_fn(s) for s in sentences]

    chunks = []
    current_chunk = [sentences[0]]
    for i in range(1, len(sentences)):
        similarity = _cosine_similarity(embeddings[i - 1], embeddings[i])
        if similarity < similarity_threshold:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sentences[i]]
        else:
            current_chunk.append(sentences[i])
    chunks.append(" ".join(current_chunk))

    return chunks

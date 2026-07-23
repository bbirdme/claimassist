from src.corpus_gen.render_pdf import SECTION_HEADERS


def _chunk_by_section_headers(text: str) -> list[str]:
    """Policy documents have known section headers (DECLARATIONS, EXCLUSIONS,
    etc.) - split on those, keeping the header as part of its chunk since
    it's useful retrieval context (a chunk that says "$2,500" is a lot less
    useful than one that says "DEDUCTIBLES AND LIMITS ... $2,500")."""
    chunks = []
    current_header = None
    current_lines = []

    def flush():
        if current_header and current_lines:
            chunks.append(current_header + "\n\n" + "\n".join(current_lines))
        elif current_lines:
            chunks.append("\n".join(current_lines))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        normalized = line.rstrip(":").strip().upper()
        if normalized in SECTION_HEADERS:
            flush()
            current_header = normalized
            current_lines = []
        elif line:
            current_lines.append(line)

    flush()
    return chunks


def _chunk_by_paragraph(text: str) -> list[str]:
    """Claims and medical notes don't have rigid section headers - fall back
    to paragraph boundaries (blank lines), which is the natural structural
    unit these document types actually have."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs


def structural_chunk(text: str, doc_type: str) -> list[str]:
    if doc_type == "policy":
        chunks = _chunk_by_section_headers(text)
        if chunks:
            return chunks
    return _chunk_by_paragraph(text)

"""
Resolves the canonical text for every document in the corpus, one text
per document - not two competing versions. For the 3 policies that got the
scan-simulation treatment, the scanned/OCR'd version is canonical, since
that's what the simulation represents: a policy that only exists as a
scanned file in production. The clean PDF for those 3 was only ever an
intermediate artifact used to *produce* the simulated scan.
"""

from dataclasses import dataclass
from pathlib import Path

from src.corpus_gen.facts import POLICIES, CLAIMS, MEDICAL_NOTES
from src.corpus_gen.render_all import SCAN_SIMULATED
from src.ingestion.extract_text import extract_text

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@dataclass
class Document:
    doc_id: str
    doc_type: str  # "policy" | "claim" | "medical_note"
    text: str
    extraction_method: str  # "direct" | "ocr" | "plain_text"


def load_corpus() -> list[Document]:
    documents = []

    for policy in POLICIES:
        number = policy["policy_number"]
        if number in SCAN_SIMULATED:
            pdf_path = DATA_DIR / "policies" / "pdf_scanned" / f"{number}.pdf"
        else:
            pdf_path = DATA_DIR / "policies" / "pdf" / f"{number}.pdf"

        result = extract_text(pdf_path)
        documents.append(
            Document(
                doc_id=number,
                doc_type="policy",
                text=result.text,
                extraction_method=result.method,
            )
        )

    for claim in CLAIMS:
        claim_id = claim["claim_id"]
        text = (DATA_DIR / "claims" / f"{claim_id}.txt").read_text()
        documents.append(
            Document(doc_id=claim_id, doc_type="claim", text=text, extraction_method="plain_text")
        )

    for note in MEDICAL_NOTES:
        note_id = note["note_id"]
        text = (DATA_DIR / "medical_notes" / f"{note_id}.txt").read_text()
        documents.append(
            Document(doc_id=note_id, doc_type="medical_note", text=text, extraction_method="plain_text")
        )

    return documents


if __name__ == "__main__":
    docs = load_corpus()
    print(f"Loaded {len(docs)} documents\n")
    for doc in docs:
        print(f"{doc.doc_id:16s} type={doc.doc_type:14s} method={doc.extraction_method:11s} chars={len(doc.text)}")

from dataclasses import dataclass
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader

# Below this many characters per page, on average, treat direct extraction as
# having failed (an empty/near-empty result from a scanned page still often
# returns a handful of stray characters, not a clean zero).
MIN_CHARS_PER_PAGE = 20


@dataclass
class ExtractionResult:
    text: str
    method: str  # "direct" or "ocr"
    page_count: int


def _extract_direct(pdf_path: Path) -> tuple[str, int]:
    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text, len(reader.pages)


def _extract_ocr(pdf_path: Path, dpi: int = 150) -> tuple[str, int]:
    images = convert_from_path(str(pdf_path), dpi=dpi)
    text = "\n".join(pytesseract.image_to_string(img) for img in images)
    return text, len(images)


def extract_text(pdf_path: Path) -> ExtractionResult:
    """Try direct text extraction first (fast, exact, no dependency on OCR
    accuracy). Only fall back to OCR if direct extraction comes back empty
    or near-empty - the signal that this PDF is actually a scanned image
    with no embedded text layer, not a normal digital document."""
    direct_text, page_count = _extract_direct(pdf_path)

    if len(direct_text.strip()) >= MIN_CHARS_PER_PAGE * page_count:
        return ExtractionResult(text=direct_text, method="direct", page_count=page_count)

    ocr_text, ocr_page_count = _extract_ocr(pdf_path)
    return ExtractionResult(text=ocr_text, method="ocr", page_count=ocr_page_count)


if __name__ == "__main__":
    data_dir = Path(__file__).parent.parent.parent / "data" / "policies"

    for label, path in [
        ("clean PDF", data_dir / "pdf" / "HO-88213-4.pdf"),
        ("simulated scan", data_dir / "pdf_scanned" / "HO-88213-4.pdf"),
    ]:
        result = extract_text(path)
        print(f"{label}: method={result.method}, pages={result.page_count}, "
              f"chars={len(result.text)}")

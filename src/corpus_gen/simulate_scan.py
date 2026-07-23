import random
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image, ImageFilter


def _degrade(image: Image.Image) -> Image.Image:
    """Make a clean rendered page look like a real scanned document: slight
    rotation (a page fed crookedly into a scanner), blur (imperfect focus),
    grayscale + JPEG recompression (typical scanner/fax artifacts)."""
    image = image.convert("L")  # grayscale, like most office scanners

    angle = random.uniform(-2.5, 2.5)
    image = image.rotate(angle, expand=True, fillcolor=255)

    image = image.filter(ImageFilter.GaussianBlur(radius=0.6))

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=55)
    buffer.seek(0)
    return Image.open(buffer).convert("L")


def simulate_scan(pdf_path: Path, out_path: Path, dpi: int = 150):
    """Rasterize a text PDF to images, degrade them to look scanned, and
    save as a new image-only PDF with no embedded text layer - so direct
    text extraction on it will find nothing, forcing an OCR fallback."""
    pages = convert_from_path(str(pdf_path), dpi=dpi)
    degraded = [_degrade(p) for p in pages]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    degraded[0].save(
        str(out_path), save_all=True, append_images=degraded[1:], format="PDF"
    )


if __name__ == "__main__":
    data_dir = Path(__file__).parent.parent.parent / "data"
    src = data_dir / "policies" / "pdf" / "HO-88213-4.pdf"
    dst = data_dir / "policies" / "pdf_scanned" / "HO-88213-4.pdf"
    simulate_scan(src, dst)
    print(f"Simulated scan written to {dst}")

from pathlib import Path

from src.corpus_gen.facts import POLICIES
from src.corpus_gen.render_pdf import render_policy_pdf
from src.corpus_gen.simulate_scan import simulate_scan

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "policies"

# One per policy type, so the OCR fallback path gets exercised across all
# three document categories, not just one.
SCAN_SIMULATED = {"HO-4471-9", "AU-2298-3", "HI-6614-2"}


def main():
    for policy in POLICIES:
        number = policy["policy_number"]
        text = (DATA_DIR / f"{number}.txt").read_text()

        pdf_path = DATA_DIR / "pdf" / f"{number}.pdf"
        render_policy_pdf(number, text, pdf_path)
        print(f"Rendered {pdf_path}")

        if number in SCAN_SIMULATED:
            scan_path = DATA_DIR / "pdf_scanned" / f"{number}.pdf"
            simulate_scan(pdf_path, scan_path)
            print(f"  -> simulated scan: {scan_path}")


if __name__ == "__main__":
    main()

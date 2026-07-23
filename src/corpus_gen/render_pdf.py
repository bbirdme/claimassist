from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

SECTION_HEADERS = {
    "DECLARATIONS",
    "COVERAGE SUMMARY",
    "DEDUCTIBLES AND LIMITS",
    "EXCLUSIONS",
    "DEFINITIONS",
}


def parse_sections(text: str) -> list[tuple[str, list[str]]]:
    """Split generated policy text into (header, lines) sections, keyed on
    the ALL-CAPS section headers the generation prompt asked for."""
    sections = []
    current_header = None
    current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        normalized = line.rstrip(":").strip().upper()
        if normalized in SECTION_HEADERS:
            line = normalized
        if line in SECTION_HEADERS:
            if current_header:
                sections.append((current_header, current_lines))
            current_header = line
            current_lines = []
        elif line and current_header:
            current_lines.append(line)

    if current_header:
        sections.append((current_header, current_lines))
    return sections


def _as_table(lines: list[str], normal_style) -> list:
    """Convert '- Label: Value' style lines into an actual PDF table,
    instead of leaving them as plain paragraphs - real policy documents
    present deductible/limit schedules as tables, and tables are exactly
    the kind of structure naive text extraction mangles."""
    rows = []
    for line in lines:
        cleaned = line.lstrip("-*• ").strip()
        if ":" in cleaned:
            label, value = cleaned.split(":", 1)
            rows.append([label.strip(), value.strip()])

    if not rows:
        return [Paragraph(" ".join(lines), normal_style)]

    table = Table([["Item", "Amount"]] + rows, colWidths=[3.5 * inch, 2 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [table]


def render_policy_pdf(policy_number: str, text: str, out_path: Path):
    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"], spaceBefore=14, spaceAfter=8
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
    )

    story = [
        Paragraph(f"Policy Document — {policy_number}", styles["Title"]),
        Spacer(1, 0.2 * inch),
    ]

    for header, lines in parse_sections(text):
        story.append(Paragraph(header, heading_style))
        if header == "DEDUCTIBLES AND LIMITS":
            story.extend(_as_table(lines, styles["Normal"]))
        else:
            for line in lines:
                story.append(Paragraph(line, styles["Normal"]))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 0.15 * inch))

    def add_footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.9 * inch, 0.5 * inch, f"{policy_number} — Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)


if __name__ == "__main__":
    data_dir = Path(__file__).parent.parent.parent / "data"
    sample_text = (data_dir / "policies" / "HO-88213-4.txt").read_text()
    out = data_dir / "policies" / "pdf" / "HO-88213-4.pdf"
    render_policy_pdf("HO-88213-4", sample_text, out)
    print(f"Rendered {out}")

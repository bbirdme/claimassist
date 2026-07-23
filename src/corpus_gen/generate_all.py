from pathlib import Path

from src.corpus_gen.facts import POLICIES, CLAIMS, MEDICAL_NOTES
from src.corpus_gen.generate_docs import (
    generate_policy_document,
    generate_claim_narrative,
    generate_medical_note,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def main():
    for policy in POLICIES:
        print(f"Generating policy {policy['policy_number']}...")
        text = generate_policy_document(policy)
        out_path = DATA_DIR / "policies" / f"{policy['policy_number']}.txt"
        out_path.write_text(text)
        print(f"  -> {out_path} ({len(text)} chars)")

    for claim in CLAIMS:
        print(f"Generating claim {claim['claim_id']}...")
        text = generate_claim_narrative(claim)
        out_path = DATA_DIR / "claims" / f"{claim['claim_id']}.txt"
        out_path.write_text(text)
        print(f"  -> {out_path} ({len(text)} chars)")

    for note in MEDICAL_NOTES:
        print(f"Generating medical note {note['note_id']}...")
        text = generate_medical_note(note)
        out_path = DATA_DIR / "medical_notes" / f"{note['note_id']}.txt"
        out_path.write_text(text)
        print(f"  -> {out_path} ({len(text)} chars)")

    print("\nDone.")


if __name__ == "__main__":
    main()

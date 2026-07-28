"""
Deliberately broken synthetic test cases - not added to the real corpus in
src/corpus_gen/facts.py, since these exist only to verify that discrepancy
detection actually catches real problems, not just correctly stays quiet on
already-clean claims (which is all the 5 real claims are).
"""

from src.corpus_gen.facts import get_policy

# Real policy HO-88213-4: effective 2025-09-01 to 2026-09-01.
# This loss date is a full year after expiration.
DATE_OUTSIDE_PERIOD = {
    "claim_id": "TEST-DATE-001",
    "policy_number": "HO-88213-4",
    "date_of_loss": "2027-03-03",
    "loss_type": "wind_hail",
    "injury": False,
    "facts": "Synthetic test case: wind/hail damage claimed a full year after the policy expired.",
}

# Real policy HO-88213-4 explicitly excludes flood damage.
EXCLUDED_LOSS_TYPE = {
    "claim_id": "TEST-EXCL-001",
    "policy_number": "HO-88213-4",
    "date_of_loss": "2026-03-03",
    "loss_type": "flood",
    "injury": False,
    "facts": "Synthetic test case: flood damage claimed against a policy that explicitly excludes flood.",
}

BROKEN_CASES = [DATE_OUTSIDE_PERIOD, EXCLUDED_LOSS_TYPE]


if __name__ == "__main__":
    import json

    from src.agents.deterministic_check import check_claim_against_policy

    for case in BROKEN_CASES:
        policy = get_policy(case["policy_number"])
        discrepancies = check_claim_against_policy(case, policy)
        print(f"{case['claim_id']}: {json.dumps(discrepancies, indent=2)}")

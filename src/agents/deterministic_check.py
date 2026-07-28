"""
A plain, deterministic discrepancy check - no LLM involved - covering the
same two checks the agent's system prompt asks for: is the date of loss
within the policy's effective period, and is the loss type excluded. Built
specifically to compare against src/agents/single_agent.py's reliability,
after the agent got CLM-2026-0301 (which has zero real discrepancies)
wrong in 8 of 10 runs.
"""

from datetime import date

from src.agents.tools import lookup_claim, lookup_policy


def check_claim(claim_id: str) -> dict:
    claim = lookup_claim(claim_id)
    if "error" in claim:
        return {"claim_id": claim_id, "discrepancies": [{"issue": "claim not found", "detail": claim["error"]}]}

    policy = lookup_policy(claim["policy_number"])
    if "error" in policy:
        return {
            "claim_id": claim_id,
            "policy_number": claim["policy_number"],
            "discrepancies": [{"issue": "policy not found", "detail": policy["error"]}],
        }

    return {
        "claim_id": claim_id,
        "policy_number": claim["policy_number"],
        "discrepancies": check_claim_against_policy(claim, policy),
    }


def check_claim_against_policy(claim: dict, policy: dict) -> list[dict]:
    """Pure logic, separated from the lookup calls above, so it can be
    exercised directly against synthetic claim/policy dicts in tests -
    without needing to add fake entries to the real corpus."""
    discrepancies = []

    loss_date = date.fromisoformat(claim["date_of_loss"])
    effective = date.fromisoformat(policy["effective_date"])
    expiration = date.fromisoformat(policy["expiration_date"])

    if not (effective <= loss_date <= expiration):
        discrepancies.append({
            "issue": "date of loss outside policy effective period",
            "detail": f"{loss_date} is not between {effective} and {expiration}",
        })

    loss_type_words = claim["loss_type"].replace("_", " ").lower()
    for exclusion in policy["exclusions"]:
        exclusion_lower = exclusion.lower()
        mentions_loss_type = loss_type_words in exclusion_lower or exclusion_lower in loss_type_words

        # A naive substring match isn't enough: an exclusion clause can carve
        # OUT the loss type via an "except" qualifier (e.g. "Mold, except
        # when directly resulting from a covered water damage event" does
        # NOT exclude water damage - it explicitly un-excludes it). Checking
        # whether the loss type appears specifically in the "except" part
        # avoids flagging exactly this case as a false positive.
        if "except" in exclusion_lower:
            except_clause = exclusion_lower.split("except", 1)[1]
            if loss_type_words in except_clause:
                continue

        if mentions_loss_type:
            discrepancies.append({
                "issue": "loss type excluded",
                "detail": f"'{claim['loss_type']}' matches exclusion: {exclusion}",
            })

    return discrepancies


if __name__ == "__main__":
    import json
    import sys

    claim_id = sys.argv[1] if len(sys.argv) > 1 else "CLM-2026-0301"
    print(json.dumps(check_claim(claim_id), indent=2))

"""
Structured lookup tools for the claim-processing agent.

Deliberately NOT semantic/vector search: claim IDs and policy numbers are
always known, exact identifiers in this task, and Phase 1 (see
docs/phase-1-hybrid-search.md) found that exact-identifier lookups are
reliably handled by structured data access, not by ranking algorithms over
free text. These tools query the ground-truth facts directly.
"""

from src.corpus_gen.facts import POLICIES, CLAIMS, MEDICAL_NOTES


def lookup_claim(claim_id: str) -> dict:
    claim = next((c for c in CLAIMS if c["claim_id"] == claim_id), None)
    if claim is None:
        return {"error": f"No claim found with ID {claim_id}"}
    return claim


def lookup_policy(policy_number: str) -> dict:
    policy = next((p for p in POLICIES if p["policy_number"] == policy_number), None)
    if policy is None:
        return {"error": f"No policy found with number {policy_number}"}
    return policy


def lookup_medical_notes(claim_id: str) -> list[dict]:
    return [n for n in MEDICAL_NOTES if n["claim_id"] == claim_id]


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_claim",
            "description": "Look up a claim's facts (date of loss, loss type, injury flag, narrative facts, and the policy number it was filed against) by claim ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "e.g. CLM-2026-0412"},
                },
                "required": ["claim_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_policy",
            "description": "Look up a policy's terms (effective/expiration dates, deductibles, coverage limits, exclusions) by policy number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_number": {"type": "string", "description": "e.g. HO-88213-4"},
                },
                "required": ["policy_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_medical_notes",
            "description": "Look up all medical notes linked to a claim ID (there may be more than one, e.g. an ER visit plus a follow-up).",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "e.g. CLM-2026-0520"},
                },
                "required": ["claim_id"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "lookup_claim": lookup_claim,
    "lookup_policy": lookup_policy,
    "lookup_medical_notes": lookup_medical_notes,
}

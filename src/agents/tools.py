"""
Structured lookup tools for the claim-processing agent.

Deliberately NOT semantic/vector search: claim IDs and policy numbers are
always known, exact identifiers in this task, and Phase 1 (see
docs/phase-1-hybrid-search.md) found that exact-identifier lookups are
reliably handled by structured data access, not by ranking algorithms over
free text.

As of Phase 3, these call the mock enterprise API over HTTP (OAuth2
client-credentials auth) instead of importing src/corpus_gen/facts.py
directly - the agent no longer has direct access to claim/policy data, the
same as it wouldn't against a real insurer's backend system. See
src/integrations/enterprise_client.py and
src/integrations/enterprise_api/main.py.
"""

from src.integrations.enterprise_client import get_claim, get_policy, get_medical_notes


def lookup_claim(claim_id: str) -> dict:
    return get_claim(claim_id)


def lookup_policy(policy_number: str) -> dict:
    return get_policy(policy_number)


def lookup_medical_notes(claim_id: str) -> list[dict]:
    return get_medical_notes(claim_id)


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

"""
Demonstrates a human actually changing the outcome, not rubber-stamping it,
using TEST-AMBIG-001 (a vandalism claim with a repair estimate below the
standard deductible - see docs/phase-2-human-in-the-loop.md).

The agent's output here is non-deterministic - across several runs it
sometimes proposed just the one genuinely useful finding (repair estimate
below deductible, meaning zero payout), and sometimes added extra entries,
including one that contradicts its own explanation (labels "vandalism may
be an intentional act" as an issue, then explains in the same breath that
it isn't actually excluded). Re-running live until an interesting case
turns up would be cherry-picking, so this demo does two things: runs the
pipeline live (showing whatever it actually produces right now), and
separately replays one specific, previously-captured multi-item response
to reliably demonstrate the override mechanism working, rather than
depending on live randomness to reproduce that exact scenario.
"""

import json

from dotenv import load_dotenv

from src.corpus_gen import facts
from src.agents.human_in_the_loop import build_hitl_graph, start_review, resume_review

CLAIM_ID = "TEST-AMBIG-001"

# A real response captured from an earlier live run on this exact claim -
# not fabricated, but not guaranteed to reproduce on any given re-run either,
# hence replaying it directly here instead of hoping to re-roll it live.
CAPTURED_PROPOSAL = [
    {
        "issue": "Claim's date_of_loss is within policy period but close to expiration",
        "detail": "The date_of_loss 2026-04-01 is within the policy period, but the policy expires soon on 2026-09-01, which may cause issues if repairs are delayed.",
    },
    {
        "issue": "Loss type potential exclusion",
        "detail": "Vandalism may be considered an intentional act, and the policy excludes intentional acts by the insured, but the facts do not indicate the insured was involved.",
    },
    {
        "issue": "Deductible may exceed repair estimate",
        "detail": "The standard deductible of $1000 exceeds the $800 repair estimate, which may result in no payout.",
    },
]


def _ensure_test_claim():
    if not any(c["claim_id"] == CLAIM_ID for c in facts.CLAIMS):
        facts.CLAIMS.append({
            "claim_id": CLAIM_ID,
            "policy_number": "HO-88213-4",
            "date_of_loss": "2026-04-01",
            "loss_type": "vandalism",
            "injury": False,
            "facts": "Someone spray-painted graffiti on the exterior wall of the home. Repair estimate $800.",
        })


def review_captured_example():
    """Reliable demo of an actual override: 2 of 3 proposed items get
    rejected by the human reviewer - one for being speculative and
    non-actionable ("may cause issues if delayed" - not a real finding
    about this claim as filed), one for contradicting its own explanation
    (calls itself an "issue" while explaining it isn't actually excluded)."""
    print("=== Replaying a captured multi-item proposal ===")
    print(json.dumps(CAPTURED_PROPOSAL, indent=2))

    approved = [d for d in CAPTURED_PROPOSAL if "deductible" in d["issue"].lower()]

    print(f"\n=== Human reviewer approves {len(approved)} of {len(CAPTURED_PROPOSAL)} ===")
    print(json.dumps(approved, indent=2))
    print("\nRejected:")
    for d in CAPTURED_PROPOSAL:
        if d not in approved:
            print(f"  - {d['issue']!r}: not an actual finding about this claim")

    _ensure_test_claim()
    graph = build_hitl_graph()
    config, _ = start_review(graph, CLAIM_ID)
    final = resume_review(graph, config, approved)

    print("\n=== Final result reflects the human's decision, not the agent's raw proposal ===")
    print(json.dumps({"discrepancies": final["discrepancies"], "summary": final["summary"]}, indent=2))


def review_live_run():
    print("\n\n=== Live run (whatever the agent produces right now) ===")
    _ensure_test_claim()
    graph = build_hitl_graph()
    config, proposed = start_review(graph, CLAIM_ID)
    print(json.dumps(proposed, indent=2))

    # Auto-approve for this smoke test - the point of this half is just to
    # show current live behavior, not to script a decision.
    final = resume_review(graph, config, proposed)
    print("\nAuto-approved as-is; final summary:")
    print(final["summary"])


if __name__ == "__main__":
    load_dotenv()
    review_captured_example()
    review_live_run()

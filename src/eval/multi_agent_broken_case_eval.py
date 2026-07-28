"""
Same check as src/eval/agent_broken_case_eval.py (does it catch real,
deliberately-planted discrepancies, not just stay quiet on clean claims),
run against the multi-agent pipeline instead - important after tightening
the discrepancy-checking prompt to stop padding the list with
confirmations, since over-correcting that could make the model
under-report real problems too.
"""

from dotenv import load_dotenv

from src.corpus_gen import facts
from src.eval.broken_claim_cases import BROKEN_CASES
from src.agents.multi_agent import run_multi_agent

N_RUNS_PER_CASE = 3


def main():
    load_dotenv()
    facts.CLAIMS.extend(BROKEN_CASES)

    for case in BROKEN_CASES:
        print(f"\n=== {case['claim_id']} ({case['facts']}) ===")
        for i in range(N_RUNS_PER_CASE):
            try:
                outcome = run_multi_agent(case["claim_id"])
                discrepancies = outcome.get("discrepancies", [])
                caught = len(discrepancies) > 0
                print(f"  run {i + 1}: {'CAUGHT' if caught else 'MISSED'} - {discrepancies}")
            except Exception as e:
                print(f"  run {i + 1}: CRASHED - {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

"""
Checks whether the agent (not just the deterministic checker) actually
catches real, deliberately-planted discrepancies - not just whether it
avoids false positives on already-clean claims. Temporarily injects the
synthetic broken cases into the in-memory CLAIMS list the agent's tools
read from; nothing is written back to the real corpus.
"""

from dotenv import load_dotenv

from src.corpus_gen import facts
from src.eval.broken_claim_cases import BROKEN_CASES
from src.agents.single_agent import run_agent

N_RUNS_PER_CASE = 3


def main():
    load_dotenv()
    facts.CLAIMS.extend(BROKEN_CASES)

    for case in BROKEN_CASES:
        print(f"\n=== {case['claim_id']} ({case['facts']}) ===")
        for i in range(N_RUNS_PER_CASE):
            try:
                outcome = run_agent(case["claim_id"])
                discrepancies = outcome["result"].get("discrepancies", [])
                caught = len(discrepancies) > 0
                print(f"  run {i + 1}: {'CAUGHT' if caught else 'MISSED'} - {discrepancies}")
            except Exception as e:
                print(f"  run {i + 1}: CRASHED - {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

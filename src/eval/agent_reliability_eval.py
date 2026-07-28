"""
Runs the single agent N times on the same claim to measure consistency,
not just correctness on one lucky/unlucky run. CLM-2026-0301 is known from
ground truth (src/corpus_gen/facts.py) to have zero real discrepancies:
date of loss (2026-03-03) falls within the policy's effective period
(2025-09-01 to 2026-09-01), and wind/hail is not excluded on HO-88213-4.
Any run reporting a discrepancy is a false positive, by construction.
"""

from dotenv import load_dotenv

from src.agents.single_agent import run_agent

CLAIM_ID = "CLM-2026-0301"
N_RUNS = 10


def classify(outcome: dict | None, error: Exception | None) -> str:
    if error is not None:
        return f"crashed: {type(error).__name__}: {error}"
    discrepancies = outcome["result"].get("discrepancies", [])
    if not discrepancies:
        return "correct (no discrepancies, matches ground truth)"
    return f"false positive: {discrepancies}"


def main():
    load_dotenv()
    results = []

    for i in range(N_RUNS):
        try:
            outcome = run_agent(CLAIM_ID)
            error = None
        except Exception as e:
            outcome = None
            error = e

        label = classify(outcome, error)
        results.append(label)
        print(f"run {i + 1}: {label}")

    print(f"\n=== Summary over {N_RUNS} runs on {CLAIM_ID} ===")
    n_correct = sum(1 for r in results if r.startswith("correct"))
    n_false_positive = sum(1 for r in results if r.startswith("false positive"))
    n_crashed = sum(1 for r in results if r.startswith("crashed"))
    print(f"correct        : {n_correct}/{N_RUNS}")
    print(f"false positive : {n_false_positive}/{N_RUNS}")
    print(f"crashed        : {n_crashed}/{N_RUNS}")


if __name__ == "__main__":
    main()

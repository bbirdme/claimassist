"""
Same reliability test as src/eval/agent_reliability_eval.py, run against
the multi-agent LangGraph pipeline instead of the single hand-rolled agent
- so the two are directly comparable on identical methodology.
"""

from dotenv import load_dotenv

from src.agents.multi_agent import run_multi_agent

CLAIM_ID = "CLM-2026-0301"
N_RUNS = 10


def classify(outcome: dict | None, error: Exception | None) -> str:
    if error is not None:
        return f"crashed: {type(error).__name__}: {error}"
    discrepancies = outcome.get("discrepancies", [])
    if not discrepancies:
        return "correct (no discrepancies, matches ground truth)"
    return f"false positive: {discrepancies}"


def main():
    load_dotenv()
    results = []

    for i in range(N_RUNS):
        try:
            outcome = run_multi_agent(CLAIM_ID)
            error = None
        except Exception as e:
            outcome = None
            error = e

        label = classify(outcome, error)
        results.append(label)
        print(f"run {i + 1}: {label}")

    print(f"\n=== Summary over {N_RUNS} runs on {CLAIM_ID} (multi-agent) ===")
    n_correct = sum(1 for r in results if r.startswith("correct"))
    n_false_positive = sum(1 for r in results if r.startswith("false positive"))
    n_crashed = sum(1 for r in results if r.startswith("crashed"))
    print(f"correct        : {n_correct}/{N_RUNS}")
    print(f"false positive : {n_false_positive}/{N_RUNS}")
    print(f"crashed        : {n_crashed}/{N_RUNS}")


if __name__ == "__main__":
    main()

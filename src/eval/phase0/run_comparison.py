import json
import re
from pathlib import Path

from dotenv import load_dotenv

from src.integrations.llm_providers import call_ollama, call_groq, call_gemini
from src.eval.phase0.prompts import PROMPTS

PROVIDERS = [call_ollama, call_groq, call_gemini]

RESULTS_PATH = Path(__file__).parent.parent.parent.parent / "docs" / "phase-0-results.json"


def try_parse_json(text: str):
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def main():
    load_dotenv()
    results = []

    for prompt in PROMPTS:
        print(f"\n=== {prompt['id']} ({prompt['category']}) ===")
        for provider_fn in PROVIDERS:
            try:
                result = provider_fn(prompt["text"])
                result["prompt_id"] = prompt["id"]
                result["category"] = prompt["category"]

                if prompt["category"] == "structured_output":
                    parsed = try_parse_json(result["response_text"])
                    result["valid_json"] = parsed is not None
                    result["parsed_json"] = parsed

                results.append(result)

                summary = (
                    f"{result['provider']:8s} | "
                    f"prompt_tokens={result['prompt_tokens']:>4} | "
                    f"completion_tokens={result['completion_tokens']:>4} | "
                    f"latency={result['latency_seconds']:.2f}s"
                )
                if prompt["category"] == "structured_output":
                    summary += f" | valid_json={result['valid_json']}"
                print(summary)

            except Exception as e:
                print(f"{provider_fn.__name__} FAILED: {e}")
                results.append({
                    "provider": provider_fn.__name__,
                    "prompt_id": prompt["id"],
                    "category": prompt["category"],
                    "error": str(e),
                })

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nFull results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()

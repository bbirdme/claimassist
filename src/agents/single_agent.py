import json
import os

from groq import Groq

from src.agents.tools import TOOL_SCHEMAS, TOOL_FUNCTIONS

SYSTEM_PROMPT = """You are a claims-processing assistant for an insurance \
company. Given a claim ID, investigate it using the available tools and \
check for discrepancies. Specifically check:

1. Is the date of loss within the policy's effective period (between its \
effective_date and expiration_date)?
2. Is the claim's loss_type actually covered - i.e. NOT one of the policy's \
listed exclusions?
3. For injury claims, do linked medical notes exist, and are they \
consistent with the claim's stated facts (same approximate date, same \
type of injury/incident)?
4. Does the claim reference a policy number that actually exists?

Use the tools to gather all necessary facts before answering. Do not guess \
or invent facts - only use what the tools return.

Once you have gathered everything needed, respond with ONLY a JSON object \
(no other text, no markdown fences) with this exact shape:
{"claim_id": "...", "policy_number": "...", "discrepancies": [{"issue": "...", "detail": "..."}], "summary": "..."}

If there are no discrepancies, "discrepancies" should be an empty list.
"""


def _to_message_dict(message) -> dict:
    result = {"role": "assistant", "content": message.content}
    if message.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in message.tool_calls
        ]
    return result


def run_agent(claim_id: str, model: str = "llama-3.3-70b-versatile", max_turns: int = 6) -> dict:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Investigate claim {claim_id}."},
    ]

    trace = []

    for turn in range(max_turns):
        resp = client.chat.completions.create(model=model, messages=messages, tools=TOOL_SCHEMAS)
        message = resp.choices[0].message
        messages.append(_to_message_dict(message))

        if not message.tool_calls:
            cleaned = message.content.strip()
            cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(cleaned)
            return {"result": result, "trace": trace, "turns": turn + 1}

        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            fn_result = TOOL_FUNCTIONS[fn_name](**fn_args)
            trace.append({"tool": fn_name, "args": fn_args, "result": fn_result})

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(fn_result),
            })

    raise RuntimeError(f"Agent did not converge within {max_turns} turns")


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    claim_id = sys.argv[1] if len(sys.argv) > 1 else "CLM-2026-0301"
    output = run_agent(claim_id)
    print(json.dumps(output, indent=2, default=str))

"""
Multi-agent version of the same claim-lookup + discrepancy-check task,
built with LangGraph instead of a hand-rolled loop (src/agents/single_agent.py).

Splits the single agent's one do-everything loop into 3 narrowly-scoped
steps, specifically to test a hypothesis raised by the single-agent
findings (docs/phase-2-single-agent.md): the single agent's errors often
came from juggling tool-calling AND reasoning AND summarizing at once
(hallucinating tool arguments, mixing correct findings with invented
extras). Does separating those responsibilities reduce the error rate?

Fact-gathering here is deliberately plain code, not an LLM step: there's no
judgment involved in "should I look up the policy" for a known claim ID -
we always need all three pieces of data, so there's nothing for an agent to
decide. This also removes the single agent's most damaging failure mode
(hallucinating a fake policy number as a tool argument) by construction,
since the real policy_number is passed along in state rather than the LLM
re-typing it from memory.
"""

import json
import os
from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from src.agents.tools import lookup_claim, lookup_policy, lookup_medical_notes

GROQ_MODEL = "llama-3.3-70b-versatile"


def _llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=GROQ_MODEL,
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ["GROQ_API_KEY"],
    )


def _parse_json(text: str):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


class AgentState(TypedDict):
    claim_id: str
    claim: dict
    policy: dict
    medical_notes: list
    discrepancies: list
    summary: str


def gather_facts(state: AgentState) -> dict:
    claim = lookup_claim(state["claim_id"])
    policy = lookup_policy(claim["policy_number"]) if "error" not in claim else {"error": "claim not found"}
    medical_notes = lookup_medical_notes(state["claim_id"])
    return {"claim": claim, "policy": policy, "medical_notes": medical_notes}


DISCREPANCY_PROMPT = """You are checking an insurance claim for discrepancies. \
All the facts you need are given below - do not invent or assume any facts \
beyond what's provided.

CLAIM: {claim}

POLICY: {policy}

MEDICAL NOTES: {medical_notes}

Check specifically:
1. Is the claim's date_of_loss within the policy's effective_date and expiration_date?
2. Is the claim's loss_type excluded under the policy's exclusions list? (Read exclusions carefully - some have "except" qualifiers that un-exclude a case, e.g. "X, except when Y" does NOT exclude Y.)
3. If the claim is marked injury=true, are there medical notes, and are they consistent with the claim's stated facts?

Note: a claim's "estimated repair cost" or "total estimated repair cost" is \
always the gross repair estimate, BEFORE the deductible is applied. The \
deductible is subtracted later, at claim payout - it is normal and correct \
for the stated total to NOT already have the deductible subtracted, and \
that is not a discrepancy.

Respond with ONLY a JSON array (no other text, no markdown fences) of \
discrepancy objects: [{{"issue": "...", "detail": "..."}}].

The array must contain ONLY genuine problems. Do NOT add an entry to confirm \
that a check passed, matched, or was "not applicable" - if a check finds no \
problem, add nothing for it at all. Do not explain your checking process in \
the array. If every check passes, the array must be exactly [] with zero \
entries - not an entry saying nothing was found, an actually empty array.
"""


def check_discrepancies(state: AgentState) -> dict:
    prompt = DISCREPANCY_PROMPT.format(
        claim=json.dumps(state["claim"]),
        policy=json.dumps(state["policy"]),
        medical_notes=json.dumps(state["medical_notes"]),
    )
    response = _llm().invoke(prompt)
    discrepancies = _parse_json(response.content)
    return {"discrepancies": discrepancies}


SUMMARY_PROMPT = """Write a 2-3 sentence plain-language summary for a case \
worker reviewing claim {claim_id} (policy {policy_number}). \
Discrepancies found: {discrepancies}

If the list is empty, say clearly that no discrepancies were found.
"""


def summarize(state: AgentState) -> dict:
    prompt = SUMMARY_PROMPT.format(
        claim_id=state["claim_id"],
        policy_number=state["policy"].get("policy_number", "unknown"),
        discrepancies=json.dumps(state["discrepancies"]),
    )
    response = _llm().invoke(prompt)
    return {"summary": response.content.strip()}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("gather_facts", gather_facts)
    graph.add_node("check_discrepancies", check_discrepancies)
    graph.add_node("summarize", summarize)

    graph.set_entry_point("gather_facts")
    graph.add_edge("gather_facts", "check_discrepancies")
    graph.add_edge("check_discrepancies", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()


def run_multi_agent(claim_id: str) -> dict:
    graph = build_graph()
    return graph.invoke({"claim_id": claim_id})


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    claim_id = sys.argv[1] if len(sys.argv) > 1 else "CLM-2026-0301"
    result = run_multi_agent(claim_id)
    print(json.dumps(result, indent=2, default=str))

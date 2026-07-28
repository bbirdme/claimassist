"""
Adds a human-approval step to the multi-agent pipeline: after the
Discrepancy Checker runs but before the Summarizer writes the
case-worker-facing text, execution pauses and waits for a human to approve,
reject, or edit the findings. Uses LangGraph's built-in interrupt/resume
primitives (a checkpointer + interrupt()) rather than hand-rolling a
pause/resume loop.

This matters given docs/phase-2-multi-agent.md's own findings: even the
tuned pipeline isn't guaranteed correct on cases harder than what's been
tested. A human reviewing before the summary is finalized is the actual
safety net, not just a phase-plan checkbox.
"""

import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command

from src.agents.multi_agent import AgentState, gather_facts, check_discrepancies, summarize


def human_review(state: AgentState) -> dict:
    decision = interrupt({
        "discrepancies": state["discrepancies"],
        "message": "Review these discrepancies before they're summarized for the case worker.",
    })
    return {"discrepancies": decision["discrepancies"]}


def build_hitl_graph():
    graph = StateGraph(AgentState)
    graph.add_node("gather_facts", gather_facts)
    graph.add_node("check_discrepancies", check_discrepancies)
    graph.add_node("human_review", human_review)
    graph.add_node("summarize", summarize)

    graph.set_entry_point("gather_facts")
    graph.add_edge("gather_facts", "check_discrepancies")
    graph.add_edge("check_discrepancies", "human_review")
    graph.add_edge("human_review", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile(checkpointer=MemorySaver())


def start_review(graph, claim_id: str):
    """Runs the graph up to the human-review interrupt. Returns (config,
    proposed_discrepancies) - config carries the thread_id needed to resume
    this exact paused run later."""
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"claim_id": claim_id}, config=config)
    proposed = result["__interrupt__"][0].value["discrepancies"]
    return config, proposed


def resume_review(graph, config, approved_discrepancies: list[dict]) -> dict:
    """Resumes a paused run with the human's final decision on what the
    discrepancies list should actually say - which may differ from what
    the agent proposed."""
    return graph.invoke(Command(resume={"discrepancies": approved_discrepancies}), config=config)


if __name__ == "__main__":
    import json
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    claim_id = sys.argv[1] if len(sys.argv) > 1 else "CLM-2026-0301"
    graph = build_hitl_graph()

    config, proposed = start_review(graph, claim_id)
    print(f"Agent proposes for {claim_id}:")
    print(json.dumps(proposed, indent=2))
    print("\n(auto-approving as-is for this smoke test)\n")

    final = resume_review(graph, config, proposed)
    print(json.dumps({"discrepancies": final["discrepancies"], "summary": final["summary"]}, indent=2))

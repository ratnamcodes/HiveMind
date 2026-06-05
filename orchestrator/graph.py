"""Minimal LangGraph state graph that wraps the ADK hello agent.

Proves the LangGraph -> ADK wrapping pattern that Phase 4 will extend
across multiple agents.
"""

from __future__ import annotations

import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from agents.hello import run_once


class OrchestratorState(TypedDict):
    input: str
    output: str
    # Reviewer's run trace in Phoenix, produced by agents.reviewer.review(). CodeArch
    # stamps it into the GitLab MR + closing note (T11). Populated once the Reviewer
    # is wired in as a graph node; absent on the current hello-only path.
    arize_trace_url: str


async def hello_node(state: OrchestratorState) -> dict[str, str]:
    """Invoke the ADK hello agent and write its final text into `output`."""
    text, _trace = await run_once(state["input"])
    return {"output": text}


def build_graph():
    graph = StateGraph(OrchestratorState)
    graph.add_node("hello", hello_node)
    graph.add_edge(START, "hello")
    graph.add_edge("hello", END)
    return graph.compile()


app = build_graph()


if __name__ == "__main__":
    result = asyncio.run(
        app.ainvoke({"input": "What's the time in Asia/Kolkata?", "output": ""})
    )
    print("=== OrchestratorState ===")
    print(result)

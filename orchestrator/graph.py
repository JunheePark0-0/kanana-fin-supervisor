from langgraph.graph import StateGraph, START, END
from orchestrator.states import OrchestratorState

from orchestrator.nodes import (
    routing_node,
    run_agents_node,
    summarize_node
)

def orchestrator_graph():
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("Routing", routing_node)
    workflow.add_node("Run Agents", run_agents_node)
    workflow.add_node("Summarize", summarize_node)

    workflow.add_edge(START, "Routing")
    workflow.add_edge("Routing", "Run Agents")
    workflow.add_edge("Run Agents", "Summarize")
    workflow.add_edge("Summarize", END)

    return workflow.compile()
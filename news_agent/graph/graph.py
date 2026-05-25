from langgraph.graph import END, StateGraph

from graph.edges import route_after_final_check, route_after_finance, route_after_internal_check
from graph.nodes import (
    cannot_answer,
    format_answer,
    gen_final_answer,
    gen_internal_answer,
    hallucination_check_final,
    hallucination_check_internal,
    query_rewrite,
    query_rewrite_retry,
    query_structuring,
    retrieve_and_rerank,
    web_search_finance,
)
from graph.state import GraphState


def build_graph_app():
    workflow = StateGraph(GraphState)
    workflow.add_node("query_rewrite", query_rewrite)
    workflow.add_node("query_structuring", query_structuring)
    workflow.add_node("retrieve_and_rerank", retrieve_and_rerank)
    workflow.add_node("gen_internal_answer", gen_internal_answer)
    workflow.add_node("hallucination_check_internal", hallucination_check_internal)
    workflow.add_node("query_rewrite_retry", query_rewrite_retry)
    workflow.add_node("web_search_finance", web_search_finance)
    workflow.add_node("gen_final_answer", gen_final_answer)
    workflow.add_node("hallucination_check_final", hallucination_check_final)
    workflow.add_node("format_answer", format_answer)
    workflow.add_node("cannot_answer", cannot_answer)

    workflow.set_entry_point("query_rewrite")
    workflow.add_edge("query_rewrite", "query_structuring")
    workflow.add_edge("query_structuring", "retrieve_and_rerank")
    workflow.add_edge("retrieve_and_rerank", "gen_internal_answer")
    workflow.add_edge("gen_internal_answer", "hallucination_check_internal")

    workflow.add_conditional_edges(
        "hallucination_check_internal",
        route_after_internal_check,
        {"retry": "query_rewrite_retry", "to_external": "web_search_finance"},
    )
    workflow.add_edge("query_rewrite_retry", "query_structuring")

    workflow.add_conditional_edges(
        "web_search_finance",
        route_after_finance,
        {"has_results": "gen_final_answer", "cannot_answer": "cannot_answer"},
    )
    workflow.add_edge("gen_final_answer", "hallucination_check_final")

    workflow.add_conditional_edges(
        "hallucination_check_final",
        route_after_final_check,
        {
            "pass": "format_answer",
            "regenerate": "gen_final_answer",
            "re_retrieve": "retrieve_and_rerank",
            "cannot_answer": "cannot_answer",
        },
    )
    workflow.add_edge("format_answer", END)
    workflow.add_edge("cannot_answer", END)
    return workflow.compile()

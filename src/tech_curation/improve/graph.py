"""LangGraph self-improvement pipeline definition."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from tech_curation.improve.nodes.analyze_patterns import analyze_patterns_node
from tech_curation.improve.nodes.apply_changes import apply_changes_node
from tech_curation.improve.nodes.generate_changes import generate_changes_node
from tech_curation.improve.nodes.parse_feedback import parse_feedback_node
from tech_curation.improve.nodes.review_proposal import review_proposal_node, should_apply
from tech_curation.improve.nodes.revise_proposal import revise_proposal_node
from tech_curation.improve.state import ImproveState


def build_improve_graph() -> StateGraph:
    graph = StateGraph(ImproveState)

    graph.add_node("parse_feedback", parse_feedback_node)
    graph.add_node("analyze_patterns", analyze_patterns_node)
    graph.add_node("generate_changes", generate_changes_node)
    graph.add_node("review_proposal", review_proposal_node)
    graph.add_node("revise_proposal", revise_proposal_node)
    graph.add_node("apply_changes", apply_changes_node)

    graph.add_edge(START, "parse_feedback")
    graph.add_edge("parse_feedback", "analyze_patterns")
    graph.add_edge("analyze_patterns", "generate_changes")
    graph.add_edge("generate_changes", "review_proposal")

    # review → revise → review loop (max 2 iterations)
    graph.add_conditional_edges(
        "review_proposal",
        should_apply,
        {"revise": "revise_proposal", "apply": "apply_changes"},
    )
    graph.add_edge("revise_proposal", "review_proposal")
    graph.add_edge("apply_changes", END)

    return graph


def get_improve_app():
    return build_improve_graph().compile()

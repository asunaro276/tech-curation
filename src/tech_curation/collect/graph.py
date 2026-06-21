"""LangGraph collection pipeline definition."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from tech_curation.collect.nodes.fetch_content import fetch_content_node
from tech_curation.collect.nodes.github import github_node
from tech_curation.collect.nodes.merge_filter import merge_filter_node
from tech_curation.collect.nodes.plan import plan_node
from tech_curation.collect.nodes.review import review_node, should_revise
from tech_curation.collect.nodes.revise import revise_node
from tech_curation.collect.nodes.rss import rss_node
from tech_curation.collect.nodes.select import select_node
from tech_curation.collect.nodes.summarize_format import summarize_format_node
from tech_curation.collect.state import CollectState


def build_collect_graph() -> StateGraph:
    graph = StateGraph(CollectState)

    graph.add_node("plan", plan_node)
    graph.add_node("github", github_node)
    graph.add_node("rss", rss_node)
    graph.add_node("merge_filter", merge_filter_node)
    graph.add_node("fetch_content", fetch_content_node)
    graph.add_node("select", select_node)
    graph.add_node("summarize_format", summarize_format_node)
    graph.add_node("review", review_node)
    graph.add_node("revise", revise_node)

    graph.add_edge(START, "plan")

    # Fan-out: plan → [github, rss] in parallel
    graph.add_edge("plan", "github")
    graph.add_edge("plan", "rss")

    # Fan-in: both parallel nodes feed into merge_filter
    graph.add_edge("github", "merge_filter")
    graph.add_edge("rss", "merge_filter")

    # filter 済みの記事だけを対象に本文フェッチ
    graph.add_edge("merge_filter", "fetch_content")
    graph.add_edge("fetch_content", "select")
    graph.add_edge("select", "summarize_format")
    graph.add_edge("summarize_format", "review")

    # review → revise → review loop (max 3 iterations)
    graph.add_conditional_edges(
        "review",
        should_revise,
        {"revise": "revise", "end": END},
    )
    graph.add_edge("revise", "review")

    return graph


def get_collect_app():
    return build_collect_graph().compile()

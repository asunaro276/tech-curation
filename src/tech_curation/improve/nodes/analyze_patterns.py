"""AnalyzePatterns node: script-based statistics + LLM qualitative interpretation."""
from __future__ import annotations

import json
from collections import defaultdict

from tech_curation.feedback.parser import FeedbackItem
from tech_curation.improve.state import ImproveState, SourceStats
from tech_curation.llm import chat


def _compute_source_stats(
    feedback_items: list[FeedbackItem],
    source_labels: list[str],
) -> list[SourceStats]:
    source_scores: dict[str, list[int]] = defaultdict(list)
    for item in feedback_items:
        if item["relevance"] is None:
            continue
        idx = item["item_index"]
        source = source_labels[idx] if idx < len(source_labels) else "unknown"
        source_scores[source].append(item["relevance"])

    stats: list[SourceStats] = []
    for source, scores in source_scores.items():
        stats.append(
            SourceStats(
                source=source,
                avg_relevance=sum(scores) / len(scores),
                count=len(scores),
            )
        )
    return stats


def _llm_qualitative_analysis(
    feedback_items: list[FeedbackItem],
    source_stats: list[SourceStats],
    overall_feedback: str,
    policy: str,
) -> str:
    comments = [f["comment"] for f in feedback_items if f["comment"]]
    has_input = comments or overall_feedback
    if not has_input:
        return "No qualitative feedback provided."

    stats_summary = json.dumps(
        [{"source": s["source"], "avg": s["avg_relevance"]} for s in source_stats],
        ensure_ascii=False,
    )

    sections: list[str] = [f"Source stats: {stats_summary}"]
    if policy:
        sections.append(f"User's standing policy:\n{policy}")
    if overall_feedback:
        sections.append(f"Overall feedback for this report:\n{overall_feedback}")
    if comments:
        sections.append("Per-item comments:\n" + "\n".join(f"- {c}" for c in comments))

    prompt = (
        "Analyze the user feedback below and identify patterns about what they like and dislike. "
        "Take the standing policy into account as a persistent preference. "
        "Be specific and concise (2-4 sentences).\n\n"
        + "\n\n".join(sections)
    )
    try:
        return chat([{"role": "user", "content": prompt}], max_tokens=300)
    except Exception as exc:
        return f"Analysis failed: {exc}"


def analyze_patterns_node(state: ImproveState) -> ImproveState:
    feedback_items = state.get("feedback_items", [])
    source_labels = state.get("source_labels", [])
    overall_feedback = state.get("overall_feedback", "")
    policy = state.get("policy", "")

    source_stats = _compute_source_stats(feedback_items, source_labels)
    qualitative = _llm_qualitative_analysis(
        feedback_items, source_stats, overall_feedback, policy
    )

    return {**state, "source_stats": source_stats, "qualitative_analysis": qualitative}

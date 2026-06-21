"""GenerateChanges node: LLM outputs structured JSON change proposal."""
from __future__ import annotations

import json

from tech_curation.improve.state import ChangeProposal, ImproveState
from tech_curation.llm import chat, MODEL_SMART

_SYSTEM = """\
You are an agent configuration optimizer. Given feedback statistics and qualitative analysis,
propose concrete configuration changes as JSON.

Output ONLY valid JSON with this schema:
{
  "param_changes": {"source_weights.github": 0.9} | null,
  "prompt_changes": {"summarize_prompt": "new prompt text"} | null,
  "topic_changes": {"add": ["new topic"], "remove": ["old topic"]} | null,
  "reason": "brief explanation"
}

Rules:
- Prefer numeric param_changes over prompt_changes
- Only include prompt_changes if the type of content desired has fundamentally changed
- param_changes keys for weights use "source_weights.<source>" format
- Other params: filter_threshold, recency_days, max_items_per_run
- Use topic_changes to add or remove collection topics based on explicit user feedback
- Only change topics when the user clearly expressed interest in adding or removing a specific topic
- topic_changes.remove: topics the user found irrelevant or explicitly said to stop collecting
- topic_changes.add: new topics the user explicitly mentioned wanting
"""


def generate_changes_node(state: ImproveState) -> ImproveState:
    source_stats = state.get("source_stats", [])
    qualitative = state.get("qualitative_analysis", "")
    feedback_items = state.get("feedback_items", [])
    overall_feedback = state.get("overall_feedback", "")

    if not feedback_items and not overall_feedback:
        return {**state, "change_proposal": None}

    stats_text = json.dumps(
        [{"source": s["source"], "avg": round(s["avg_relevance"], 2), "n": s["count"]} for s in source_stats],
        ensure_ascii=False,
    )
    sections = [f"Source statistics:\n{stats_text}"]
    if overall_feedback:
        sections.append(f"Overall feedback from user:\n{overall_feedback}")
    sections.append(f"Qualitative analysis:\n{qualitative}")
    prompt = "\n\n".join(sections) + "\n\nPropose configuration changes to improve content relevance."

    errors = list(state.get("errors", []))
    try:
        raw = chat(
            [{"role": "user", "content": prompt}],
            max_tokens=512,
            system=_SYSTEM,
            model=MODEL_SMART,
        )
        print(f"[generate_changes] LLM raw: {raw!r}")
        data = json.loads(raw)
        topic_changes_raw = data.get("topic_changes")
        topic_changes = None
        if isinstance(topic_changes_raw, dict):
            add = [str(t) for t in topic_changes_raw.get("add", []) if t]
            remove = [str(t) for t in topic_changes_raw.get("remove", []) if t]
            if add or remove:
                topic_changes = {"add": add, "remove": remove}

        # prompt_changes must be a dict; LLM sometimes returns a plain string
        prompt_changes = data.get("prompt_changes")
        if not isinstance(prompt_changes, dict):
            prompt_changes = None

        proposal = ChangeProposal(
            param_changes=data.get("param_changes"),
            prompt_changes=prompt_changes,
            topic_changes=topic_changes,
            reason=data.get("reason", ""),
        )
        print(f"[generate_changes] proposal: {proposal}")
    except Exception as exc:
        errors.append(f"generate_changes failed: {exc}")
        print(f"[generate_changes] ERROR: {exc}")
        proposal = None

    return {**state, "change_proposal": proposal, "errors": errors}

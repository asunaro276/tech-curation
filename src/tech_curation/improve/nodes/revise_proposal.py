"""ReviseProposal node: regenerates change proposal incorporating review issues."""
from __future__ import annotations

import json

from tech_curation.improve.state import ChangeProposal, ImproveState
from tech_curation.llm import chat, MODEL_SMART

_SYSTEM = """\
You are an agent configuration optimizer. A previous proposal was reviewed and found to have issues.
Given the original feedback, previous proposal, and the review issues, output a corrected proposal.

Output ONLY valid JSON with this schema:
{
  "param_changes": {"source_weights.github": 0.9} | null,
  "prompt_changes": {"summarize_prompt": "new prompt text"} | null,
  "topic_changes": {"add": ["new topic"], "remove": ["old topic"]} | null,
  "reason": "brief explanation"
}

Rules:
- Address the review issues while staying faithful to the user's actual feedback
- Prefer numeric param_changes over prompt_changes
- param_changes keys for weights use "source_weights.<source>" format
- Other params: filter_threshold, recency_days, max_items_per_run
- Only change topics when the user clearly expressed interest in adding or removing a specific topic
"""


def revise_proposal_node(state: ImproveState) -> ImproveState:
    proposal = state.get("change_proposal")
    issues = state.get("proposal_review_issues", [])
    feedback_items = state.get("feedback_items", [])
    overall_feedback = state.get("overall_feedback", "")
    qualitative = state.get("qualitative_analysis", "")

    comments = [f["comment"] for f in feedback_items if f["comment"]]
    sections: list[str] = []
    if overall_feedback:
        sections.append(f"Overall feedback:\n{overall_feedback}")
    if comments:
        sections.append("Per-item comments:\n" + "\n".join(f"- {c}" for c in comments))
    sections.append(f"Analysis:\n{qualitative}")
    if proposal:
        sections.append(f"Previous proposal:\n{json.dumps(proposal, ensure_ascii=False, indent=2)}")
    sections.append("Review issues:\n" + "\n".join(f"- {i}" for i in issues))

    prompt = "\n\n".join(sections) + "\n\nGenerate a corrected configuration change proposal."

    errors = list(state.get("errors", []))
    try:
        raw = chat(
            [{"role": "user", "content": prompt}],
            max_tokens=512,
            system=_SYSTEM,
            model=MODEL_SMART,
        )
        print(f"[revise_proposal] raw={raw!r}")
        data = json.loads(raw)

        topic_changes_raw = data.get("topic_changes")
        topic_changes = None
        if isinstance(topic_changes_raw, dict):
            add = [str(t) for t in topic_changes_raw.get("add", []) if t]
            remove = [str(t) for t in topic_changes_raw.get("remove", []) if t]
            if add or remove:
                topic_changes = {"add": add, "remove": remove}

        prompt_changes = data.get("prompt_changes")
        if not isinstance(prompt_changes, dict):
            prompt_changes = None

        revised = ChangeProposal(
            param_changes=data.get("param_changes"),
            prompt_changes=prompt_changes,
            topic_changes=topic_changes,
            reason=data.get("reason", ""),
        )
        print(f"[revise_proposal] revised={revised}")
        return {"change_proposal": revised, "errors": errors}
    except Exception as exc:
        errors.append(f"revise_proposal failed: {exc}")
        print(f"[revise_proposal] ERROR: {exc}")
        return {"errors": errors}

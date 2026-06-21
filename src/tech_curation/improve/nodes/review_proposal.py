"""ReviewProposal node: checks whether the generated change proposal is appropriate."""
from __future__ import annotations

import json

from tech_curation.improve.state import ImproveState
from tech_curation.llm import chat, MODEL_SMART

MAX_ITERATIONS = 2

_SYSTEM = """\
You review an agent configuration change proposal and determine if it is appropriate.

Given the user feedback and the proposed changes, check:
1. Are the changes proportional to the feedback? (not too aggressive or too conservative)
2. Do the changes address what the user actually asked for?
3. Are there any clearly wrong or contradictory changes?

If the proposal is acceptable, reply with exactly: OK
If there are issues, describe them briefly in 1-3 sentences.
"""


def review_proposal_node(state: ImproveState) -> ImproveState:
    proposal = state.get("change_proposal")
    iterations = state.get("proposal_review_iterations", 0) + 1

    if not proposal:
        return {"proposal_review_issues": [], "proposal_review_iterations": iterations}

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
    sections.append(f"Proposed changes:\n{json.dumps(proposal, ensure_ascii=False, indent=2)}")

    prompt = "\n\n".join(sections)

    try:
        raw = chat(
            [{"role": "user", "content": prompt}],
            max_tokens=256,
            system=_SYSTEM,
            model=MODEL_SMART,
        ).strip()
        print(f"[review_proposal] iter={iterations} raw={raw!r}")
        issues = [] if raw == "OK" else [raw]
    except Exception as exc:
        print(f"[review_proposal] ERROR: {exc}")
        issues = []

    return {"proposal_review_issues": issues, "proposal_review_iterations": iterations}


def should_apply(state: ImproveState) -> str:
    issues = state.get("proposal_review_issues", [])
    iterations = state.get("proposal_review_iterations", 0)
    if issues and iterations < MAX_ITERATIONS:
        return "revise"
    return "apply"

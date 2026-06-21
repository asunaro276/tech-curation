"""ParseFeedback node: reads note from vault and extracts HTML comment feedback."""
from __future__ import annotations

import os
from pathlib import Path

from tech_curation.feedback.parser import (
    extract_source_from_section,
    parse_feedback,
    parse_overall_feedback,
)
from tech_curation.improve.state import ImproveState

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))
POLICY_PATH = "agent-config/policy.md"


def parse_feedback_node(state: ImproveState) -> ImproveState:
    errors = list(state.get("errors", []))

    note_path = state["note_path"]
    full_path = VAULT_ROOT / note_path
    try:
        note_content = full_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append(f"Note not found: {full_path}")
        return {**state, "errors": errors}

    feedback_items = parse_feedback(note_content)
    overall_feedback = parse_overall_feedback(note_content)
    source_labels = extract_source_from_section(note_content)

    policy_path = VAULT_ROOT / POLICY_PATH
    policy = policy_path.read_text(encoding="utf-8") if policy_path.exists() else ""

    print(f"[parse_feedback] items={len(feedback_items)}, overall={overall_feedback!r:.80}, policy_len={len(policy)}")
    return {
        **state,
        "note_content": note_content,
        "feedback_items": feedback_items,
        "overall_feedback": overall_feedback,
        "policy": policy,
        "source_labels": source_labels,
        "errors": errors,
    }

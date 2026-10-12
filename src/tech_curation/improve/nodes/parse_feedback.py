"""ParseFeedback node: reads note from vault and extracts HTML comment feedback."""
from __future__ import annotations

import os
from pathlib import Path

from tech_curation.feedback.parser import (
    DUP_PAST,
    FeedbackItem,
    extract_source_from_section,
    parse_feedback,
    parse_overall_feedback,
)
from tech_curation.improve.state import ImproveState
from tech_curation.obsidian.records import read_record

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))
POLICY_PATH = "agent-config/policy.md"


def describe_duplicates(feedback_items: list[FeedbackItem], record: dict | None) -> list[str]:
    """dup フィードバックを、items.json のタイトルを添えた説明文にする。記録がなければ番号だけで書く。"""
    titles: dict[int, str] = {}
    if record:
        for group in record.get("groups", []):
            if isinstance(group, dict):
                titles[int(group.get("no", 0))] = group.get("title", "")

    def label(no: int) -> str:
        return f"#{no}「{titles[no]}」" if titles.get(no) else f"#{no}"

    lines: list[str] = []
    for item in feedback_items:
        dup = item.get("dup", "")
        if not dup:
            continue
        no = item["item_index"] + 1
        if dup == DUP_PAST:
            lines.append(f"{label(no)} は過去のレポートで読んだ話題だった（過去との重複の見逃し）")
        elif dup.isdigit():
            lines.append(f"{label(no)} は {label(int(dup))} と同じ話題だった（まとめ漏れ）")
    return lines


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
    # レポートと同じディレクトリの items.json から、dup が指すグループのタイトルを引く
    record = read_record(VAULT_ROOT, Path(note_path).parent.name)
    duplicate_feedback = describe_duplicates(feedback_items, record)
    overall_feedback = parse_overall_feedback(note_content)
    source_labels = extract_source_from_section(note_content)

    policy_path = VAULT_ROOT / POLICY_PATH
    policy = policy_path.read_text(encoding="utf-8") if policy_path.exists() else ""

    print(f"[parse_feedback] items={len(feedback_items)}, overall={overall_feedback!r:.80}, policy_len={len(policy)}")
    return {
        **state,
        "note_content": note_content,
        "feedback_items": feedback_items,
        "duplicate_feedback": duplicate_feedback,
        "overall_feedback": overall_feedback,
        "policy": policy,
        "source_labels": source_labels,
        "errors": errors,
    }

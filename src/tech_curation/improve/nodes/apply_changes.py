"""ApplyChanges node: applies LLM JSON proposal to prompts.md and updates note status."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from tech_curation.config.settings import update_config
from tech_curation.improve.state import ImproveState

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))
PROMPTS_PATH = VAULT_ROOT / "agent-config" / "prompts.md"
HISTORY_PATH = VAULT_ROOT / "agent-config" / "feedback-history.json"
TOPICS_PATH = VAULT_ROOT / "agent-config" / "topics.md"


def _parse_section_topics(text: str, section: str) -> list[str]:
    m = re.search(rf"## {re.escape(section)}\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if not m:
        return []
    return [line.strip()[2:].strip() for line in m.group(1).splitlines() if line.strip().startswith("- ")]


def _rebuild_section(topics: list[str]) -> str:
    return "".join(f"- {t}\n" for t in topics)


def _apply_topic_changes(topics_path: Path, add: list[str], remove: list[str]) -> None:
    if not topics_path.exists():
        return
    text = topics_path.read_text(encoding="utf-8")

    active = _parse_section_topics(text, "アクティブ")
    inactive = _parse_section_topics(text, "非アクティブ")

    def find_case_insensitive(lst: list[str], name: str) -> str | None:
        for item in lst:
            if item.lower() == name.lower():
                return item
        return None

    for t in remove:
        existing = find_case_insensitive(active, t)
        if existing:
            active.remove(existing)
        if not find_case_insensitive(inactive, t):
            inactive.append(existing or t)

    for t in add:
        # ASCII以外のみのトピック（日本語等）は技術キーワードとして機能しないため追加しない
        if not t.isascii():
            print(f"[apply_changes] skip non-ASCII topic: {t}")
            continue
        if not find_case_insensitive(active, t):
            active.append(t)
        existing_inactive = find_case_insensitive(inactive, t)
        if existing_inactive:
            inactive.remove(existing_inactive)

    text = re.sub(
        r"(## アクティブ\n).*?(?=\n## |\Z)",
        lambda _: f"## アクティブ\n{_rebuild_section(active)}",
        text, flags=re.DOTALL,
    )
    text = re.sub(
        r"(## 非アクティブ\n).*?(?=\n## |\Z)",
        lambda _: f"## 非アクティブ\n{_rebuild_section(inactive)}",
        text, flags=re.DOTALL,
    )
    topics_path.write_text(text, encoding="utf-8")
    print(f"[apply_changes] topics updated: add={add}, remove={remove}")


def _update_note_status(note_content: str) -> str:
    return re.sub(r"^status:\s*draft", "status: submitted", note_content, flags=re.MULTILINE)


def _append_feedback_history(
    history_path: Path,
    note_path: str,
    feedback_items: list,
    reason: str,
    date: str,
) -> None:
    history: list[dict] = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []

    entry = {
        "timestamp": date,
        "note_path": note_path,
        "feedback": feedback_items,
        "change_reason": reason,
    }
    history.append(entry)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_changes_node(state: ImproveState) -> ImproveState:
    errors = list(state.get("errors", []))
    proposal = state.get("change_proposal")
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[apply_changes] proposal={proposal}, errors_so_far={errors}")

    if proposal:
        try:
            update_config(
                PROMPTS_PATH,
                param_changes=proposal.get("param_changes"),
                prompt_changes=proposal.get("prompt_changes"),
                reason=proposal.get("reason", ""),
                date=date,
            )
            print(f"[apply_changes] update_config done")
        except Exception as exc:
            errors.append(f"update_config failed: {exc}")
            print(f"[apply_changes] update_config ERROR: {exc}")

        topic_changes = proposal.get("topic_changes")
        if topic_changes:
            try:
                _apply_topic_changes(
                    TOPICS_PATH,
                    add=topic_changes.get("add", []),
                    remove=topic_changes.get("remove", []),
                )
            except Exception as exc:
                errors.append(f"topic_changes failed: {exc}")
                print(f"[apply_changes] topic_changes ERROR: {exc}")

    note_path = state["note_path"]
    note_content = state.get("note_content", "")
    print(f"[apply_changes] note_path={note_path!r}, content_len={len(note_content)}")
    updated_note = _update_note_status(note_content)
    status_changed = updated_note != note_content
    print(f"[apply_changes] status_changed={status_changed}")

    full_note_path = VAULT_ROOT / note_path
    try:
        full_note_path.write_text(updated_note, encoding="utf-8")
    except Exception as exc:
        errors.append(f"note status update failed: {exc}")
        print(f"[apply_changes] note write ERROR: {exc}")

    try:
        _append_feedback_history(
            HISTORY_PATH,
            note_path=note_path,
            feedback_items=state.get("feedback_items", []),
            reason=proposal["reason"] if proposal else "no changes",
            date=date,
        )
    except Exception as exc:
        errors.append(f"feedback history append failed: {exc}")

    return {**state, "note_content": updated_note, "errors": errors}

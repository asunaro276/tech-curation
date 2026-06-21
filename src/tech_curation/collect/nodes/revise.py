"""Revise node: applies review issues — removes items or rewrites summaries."""
from __future__ import annotations

import re

from tech_curation.collect.state import CollectState
from tech_curation.llm import chat

_PREAMBLE_RE = re.compile(
    r"^(?:(?:以下[はにが]|ご依頼|下記[はに])[^\n]*\n+|---\n+|\n+)+"
)


def _clean_summary(text: str) -> str:
    """前置き除去・Markdown ヘッダ太字化・コードブロック補完。"""
    text = _PREAMBLE_RE.sub("", text)
    text = re.sub(r"^#{1,3} (.+)$", r"**\1**", text, flags=re.MULTILINE)
    if text.count("```") % 2 != 0:
        text = text.rstrip() + "\n```"
    return text.strip()


def revise_node(state: CollectState) -> CollectState:
    items = list(state.get("formatted_items", []))
    issues = state.get("review_issues", [])
    config = state["config"]
    topics = state.get("topics", [])
    topic_str = "、".join(topics) if topics else ""

    remove_indices = {
        issue["item_index"]
        for issue in issues
        if issue["action"] == "remove"
    }
    rewrite_map = {
        issue["item_index"]: issue
        for issue in issues
        if issue["action"] == "rewrite"
    }

    revised: list = []
    for i, item in enumerate(items):
        if i in remove_indices:
            print(f"[revise] remove [{i}]: {item['title'][:60]}")
            continue
        if i in rewrite_map:
            issue = rewrite_map[i]
            hint = issue["rewrite_hint"]
            prompt = (
                f"関心トピック: {topic_str}\n"
                f"改善指示: {hint}\n\n"
                f"{config.summarize_prompt}\n\n"
                f"Article:\nTitle: {item['title']}\n\n{item['body'][:1000]}"
            )
            try:
                new_summary = _clean_summary(chat([{"role": "user", "content": prompt}], max_tokens=256))
                print(f"[revise] rewrite [{i}]: {item['title'][:60]}")
                revised.append({**item, "summary": new_summary})
            except Exception as exc:
                print(f"[revise] rewrite error [{i}]: {exc}")
                revised.append(item)
        else:
            revised.append(item)

    return {"formatted_items": revised}

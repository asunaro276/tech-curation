"""Generates daily Markdown report with all topics combined."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from urllib.parse import quote

from tech_curation.collect.state import CollectedItem
from tech_curation.obsidian.templates import format_item

AGENT_VERSION = "0.1.0"


def number_items(items_by_topic: dict[str, list[CollectedItem]]) -> list[tuple[int, str, CollectedItem]]:
    """レポートに載る順に 1 からの通し番号を振る。レポートと items.json で同じ番号を使う。"""
    numbered: list[tuple[int, str, CollectedItem]] = []
    for topic, items in items_by_topic.items():
        for item in items:
            numbered.append((len(numbered) + 1, topic, item))
    return numbered


def generate_daily_report(
    items_by_topic: dict[str, list[CollectedItem]],
    *,
    api_gateway_url: str = "",
    date_str: str | None = None,
) -> tuple[str, str]:
    """Return (filename, markdown_content) combining all topics into one daily file."""
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"tech-curation/{date_str}/daily.md"

    frontmatter = (
        "---\n"
        f"date: {date_str}\n"
        f"agent_version: {AGENT_VERSION}\n"
        "status: draft\n"
        "---\n\n"
    )

    header = (
        f"# Tech Curation {date_str}\n\n"
        f"*Generated {date_str} by tech-curation agent*\n\n"
        "<!-- overall: comment= -->\n\n"
    )

    sections_by_topic: dict[str, list[str]] = {}
    for no, topic, item in number_items(items_by_topic):
        sections_by_topic.setdefault(topic, []).append(format_item(item, no))
    body_parts = [f"## {topic}\n\n" + "\n".join(sections) for topic, sections in sections_by_topic.items()]

    body = "\n---\n\n".join(body_parts)

    feedback_block = ""
    if api_gateway_url:
        encoded = quote(filename, safe="")
        url = f"{api_gateway_url}/improve?note_path={encoded}"
        api_token = os.environ.get("API_TOKEN", "")
        if api_token:
            url += f"&token={quote(api_token, safe='')}"
        feedback_block = f"\n---\n\n[📤 フィードバックを送信]({url})\n"

    content = frontmatter + header + body + feedback_block
    return filename, content

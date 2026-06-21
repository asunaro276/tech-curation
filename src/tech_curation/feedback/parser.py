"""Parses <!-- fb: relevance=N, comment=text --> from Markdown files."""
from __future__ import annotations

import re
from typing import TypedDict

_FB_RE = re.compile(
    r"<!--\s*fb:\s*relevance=([^,]*),\s*comment=(.*?)\s*-->",
    re.IGNORECASE | re.DOTALL,
)


class FeedbackItem(TypedDict):
    item_index: int
    relevance: int | None
    comment: str


def parse_feedback(markdown: str) -> list[FeedbackItem]:
    """Return only feedback items where relevance or comment is non-empty."""
    results: list[FeedbackItem] = []
    for idx, match in enumerate(_FB_RE.finditer(markdown)):
        relevance_raw = match.group(1).strip()
        comment_raw = match.group(2).strip()

        if not relevance_raw and not comment_raw:
            continue

        relevance: int | None = None
        if relevance_raw:
            try:
                relevance = int(relevance_raw)
            except ValueError:
                pass

        results.append(
            FeedbackItem(
                item_index=idx,
                relevance=relevance,
                comment=comment_raw,
            )
        )
    return results


def extract_source_from_section(markdown: str) -> list[str]:
    """Extract **Source:** values from each report section."""
    return re.findall(r"\*\*Source:\*\*\s*(\w+)", markdown)


_OVERALL_RE = re.compile(
    r"<!--\s*overall:\s*comment=(.*?)\s*-->",
    re.IGNORECASE | re.DOTALL,
)


def parse_overall_feedback(markdown: str) -> str:
    """Return the overall comment for the note, or empty string if not set."""
    m = _OVERALL_RE.search(markdown)
    if not m:
        return ""
    return m.group(1).strip()

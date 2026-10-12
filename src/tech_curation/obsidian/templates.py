"""Content-type-specific Markdown formatting templates (one section per topic group)."""
from __future__ import annotations

from tech_curation.collect.state import CollectedItem

FEEDBACK_COMMENT = "<!-- fb: relevance=, dup=, comment= -->"


def _thumbnail_line(item: CollectedItem) -> str:
    url = item.get("thumbnail", "")
    if not url:
        return ""
    return f"![|400]({url})\n\n"


def _follow_line(item: CollectedItem) -> str:
    ref = item.get("follow_of")
    if not ref:
        return ""
    return f"📎 続報: [[tech-curation/{ref['date']}/daily|{ref['date']}]] の「{ref['title']}」\n\n"


def _links_block(item: CollectedItem) -> str:
    """代表記事を先頭に、グループ内の全記事へのリンクを並べる。"""
    lines = [f"- [{a['title']}]({a['url']}) — {a['source']}" for a in [item, *item.get("related", [])]]
    return "**関連記事**\n" + "\n".join(lines) + "\n\n"


def _section(item: CollectedItem, no: int) -> str:
    return f"""### #{no} [{item['title']}]({item['url']})

{_follow_line(item)}{_thumbnail_line(item)}**Source:** {item['source']} | **Date:** {item['published'][:10]}

{item['summary']}

{_links_block(item)}{FEEDBACK_COMMENT}
"""


def _code_template(item: CollectedItem, no: int) -> str:
    return _section(item, no)


def _comparison_template(item: CollectedItem, no: int) -> str:
    return _section(item, no)


def _trend_template(item: CollectedItem, no: int) -> str:
    return _section(item, no)


_TEMPLATES = {
    "code": _code_template,
    "comparison": _comparison_template,
    "trend": _trend_template,
}


def format_item(item: CollectedItem, no: int) -> str:
    """no はレポート全体での通し番号（フィードバックの dup= が指す番号）。"""
    template_fn = _TEMPLATES.get(item.get("content_type", "trend"), _trend_template)
    return template_fn(item, no)

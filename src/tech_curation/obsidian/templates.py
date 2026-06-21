"""Content-type-specific Markdown formatting templates."""
from __future__ import annotations

from tech_curation.collect.state import CollectedItem


def _thumbnail_line(item: CollectedItem) -> str:
    url = item.get("thumbnail", "")
    if not url:
        return ""
    return f"![|400]({url})\n\n"


def _code_template(item: CollectedItem, idx: int) -> str:
    return f"""### [{item['title']}]({item['url']})

{_thumbnail_line(item)}**Source:** {item['source']} | **Date:** {item['published'][:10]}

{item['summary']}

<!-- fb: relevance=, comment= -->
"""


def _comparison_template(item: CollectedItem, idx: int) -> str:
    return f"""### [{item['title']}]({item['url']})

{_thumbnail_line(item)}**Source:** {item['source']} | **Date:** {item['published'][:10]}

{item['summary']}

<!-- fb: relevance=, comment= -->
"""


def _trend_template(item: CollectedItem, idx: int) -> str:
    return f"""### [{item['title']}]({item['url']})

{_thumbnail_line(item)}**Source:** {item['source']} | **Date:** {item['published'][:10]}

{item['summary']}

<!-- fb: relevance=, comment= -->
"""


_TEMPLATES = {
    "code": _code_template,
    "comparison": _comparison_template,
    "trend": _trend_template,
}


def format_item(item: CollectedItem, idx: int) -> str:
    template_fn = _TEMPLATES.get(item.get("content_type", "trend"), _trend_template)
    return template_fn(item, idx)

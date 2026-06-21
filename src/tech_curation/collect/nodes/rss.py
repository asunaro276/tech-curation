"""RSS node: fetches items from RSS/Atom feeds using feedparser."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import feedparser

from tech_curation.collect.state import CollectedItem, CollectState

DEFAULT_FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://zenn.dev/feed",
    "https://qiita.com/popular-items/feed",
]

FEEDS_VAULT_PATH = "agent-config/feeds.md"


import re as _re

_FEED_LINE_RE = _re.compile(r"^-\s+(https?://\S+?)(?:\s+\[([^\]]+)\])?\s*$")


def _parse_feeds_md(text: str) -> list[tuple[str, str]]:
    """feeds.md の ## アクティブ セクションを解析して (url, topic_hint) のリストを返す。
    行末の [トピック名] がトピックヒント。省略時は空文字。"""
    entries: list[tuple[str, str]] = []
    in_active = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## アクティブ":
            in_active = True
            continue
        if stripped.startswith("## "):
            in_active = False
        if in_active:
            m = _FEED_LINE_RE.match(stripped)
            if m:
                entries.append((m.group(1), m.group(2) or ""))
    return entries


def _source_label(url: str) -> str:
    if "ycombinator" in url:
        return "hackernews"
    if "zenn.dev" in url:
        return "zenn"
    if "qiita.com" in url:
        return "qiita"
    if "jser.info" in url:
        return "jser"
    if "codezine.jp" in url:
        return "codezine"
    if "substack" in url:
        return "substack"
    return "rss"


# techfeed.io チャンネル URL → トピック名の対応（topics.md と一致させる）
_FEED_TOPIC_MAP: dict[str, str] = {
    "channels/TypeScript": "TypeScript/JavaScript",
    "channels/Ruby?": "Ruby",
    "zenn.dev/topics/ruby": "Ruby",
    "zenn.dev/topics/rails": "Ruby on Rails",
    "channels/Vue.js": "vue",
    "channels/Go?": "Go",
    "channels/PostgreSQL": "postgresql",
    "blog.vuejs.org": "vue",
    "zenn.dev/topics/vue": "vue",
    "zenn.dev/topics/go": "Go",
    "planet.postgresql.org": "postgresql",
    "jser.info": "TypeScript/JavaScript",
}


def _feed_topic_hint_from_url(url: str) -> str:
    """feeds.md に [トピック名] が無い場合の URL ベースのフォールバック。"""
    for pattern, topic in _FEED_TOPIC_MAP.items():
        if pattern in url:
            return topic
    return ""


def _entry_to_item(entry, source_label: str, topic_hint: str = "") -> CollectedItem:
    published = ""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        published = dt.isoformat()
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        published = dt.isoformat()
    else:
        published = datetime.now(timezone.utc).isoformat()

    body = getattr(entry, "summary", "") or getattr(entry, "description", "")

    return CollectedItem(
        id=str(uuid.uuid4()),
        title=getattr(entry, "title", ""),
        url=getattr(entry, "link", ""),
        source=source_label,
        published=published,
        body=body,
        relevance_score=0.0,
        summary="",
        content_type="",
        thumbnail="",
        topic=topic_hint,
    )


def _fetch_feed(url: str, topic_hint: str = "") -> list[CollectedItem]:
    label = _source_label(url)
    hint = topic_hint or _feed_topic_hint_from_url(url)
    feed = feedparser.parse(url)
    return [_entry_to_item(entry, label, hint) for entry in feed.entries]


_DEFAULT_FEED_ENTRIES = [(url, "") for url in DEFAULT_FEEDS]


def rss_node(state: CollectState) -> CollectState:
    vault_root = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))
    feeds_path = vault_root / FEEDS_VAULT_PATH

    if feeds_path.exists():
        feed_entries = _parse_feeds_md(feeds_path.read_text(encoding="utf-8"))
        if not feed_entries:
            feed_entries = list(_DEFAULT_FEED_ENTRIES)
    else:
        feed_entries = list(_DEFAULT_FEED_ENTRIES)

    config = state["config"]
    base_per_feed = max(15, config.max_items_per_run // max(len(feed_entries) // 3, 1))

    items: list[CollectedItem] = []
    errors: list[str] = []

    for url, topic_hint in feed_entries:
        try:
            fetched = _fetch_feed(url, topic_hint)
            source = _source_label(url)
            weight = config.source_weights.get(source, 1.0)
            per_feed = max(5, round(base_per_feed * weight))
            items.extend(fetched[:per_feed])
        except Exception as exc:
            errors.append(f"rss:{url}:{exc}")

    return {"raw_items": items, "errors": errors}

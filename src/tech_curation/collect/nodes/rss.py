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


def _parse_feeds_md(text: str) -> list[str]:
    urls: list[str] = []
    in_active = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## アクティブ":
            in_active = True
            continue
        if stripped.startswith("## "):
            in_active = False
        if in_active and stripped.startswith("- "):
            url = stripped[2:].strip()
            if url.startswith("http"):
                urls.append(url)
    return urls


def _source_label(url: str) -> str:
    if "ycombinator" in url:
        return "hackernews"
    if "zenn.dev" in url:
        return "zenn"
    if "qiita.com" in url:
        return "qiita"
    if "substack" in url:
        return "substack"
    return "rss"


def _entry_to_item(entry, source_label: str) -> CollectedItem:
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
    )


def _fetch_feed(url: str) -> list[CollectedItem]:
    label = _source_label(url)
    feed = feedparser.parse(url)
    return [_entry_to_item(entry, label) for entry in feed.entries]


def rss_node(state: CollectState) -> CollectState:
    vault_root = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))
    feeds_path = vault_root / FEEDS_VAULT_PATH

    if feeds_path.exists():
        feed_urls = _parse_feeds_md(feeds_path.read_text(encoding="utf-8"))
        if not feed_urls:
            feed_urls = list(DEFAULT_FEEDS)
    else:
        feed_urls = list(DEFAULT_FEEDS)

    config = state["config"]
    max_per_feed = max(5, config.max_items_per_run // max(len(feed_urls), 1))

    items: list[CollectedItem] = []
    errors: list[str] = []

    for url in feed_urls:
        try:
            fetched = _fetch_feed(url)
            items.extend(fetched[:max_per_feed])
        except Exception as exc:
            errors.append(f"rss:{url}:{exc}")

    return {"raw_items": items, "errors": errors}

"""Unit tests for information collection pipeline nodes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from tech_curation.collect.nodes.merge_filter import (
    _dedup_by_url,
    _filter_by_date,
)
from tech_curation.collect.nodes.plan import _parse_active_topics
from tech_curation.collect.nodes.rss import _entry_to_item
from tech_curation.collect.state import CollectedItem
from tech_curation.config.settings import AgentConfig


def _make_item(url: str = "https://example.com", days_ago: int = 0) -> CollectedItem:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return CollectedItem(
        id="test",
        title="Test Item",
        url=url,
        source="rss",
        published=dt.isoformat(),
        body="body text",
        relevance_score=0.0,
        summary="",
        content_type="",
    )


class TestParseActiveTopics:
    def test_extracts_active_topics(self):
        md = "# Topics\n\n## アクティブ\n- Rust async ecosystem\n- LLM inference\n\n## 停止中\n- Kubernetes\n"
        topics = _parse_active_topics(md)
        assert topics == ["Rust async ecosystem", "LLM inference"]

    def test_stopped_topics_excluded(self):
        md = "## アクティブ\n- Topic A\n\n## 停止中\n- Topic B\n"
        topics = _parse_active_topics(md)
        assert "Topic B" not in topics

    def test_empty_active_section(self):
        md = "## アクティブ\n\n## 停止中\n- Topic A\n"
        assert _parse_active_topics(md) == []


class TestDedup:
    def test_removes_duplicate_urls(self):
        items = [_make_item("https://a.com"), _make_item("https://a.com"), _make_item("https://b.com")]
        result = _dedup_by_url(items)
        assert len(result) == 2
        assert {i["url"] for i in result} == {"https://a.com", "https://b.com"}

    def test_preserves_first_occurrence(self):
        items = [_make_item("https://a.com"), _make_item("https://a.com")]
        items[0]["title"] = "First"
        items[1]["title"] = "Second"
        result = _dedup_by_url(items)
        assert result[0]["title"] == "First"


class TestDateFilter:
    def test_recent_item_kept(self):
        items = [_make_item(days_ago=3)]
        result = _filter_by_date(items, recency_days=7)
        assert len(result) == 1

    def test_old_item_excluded(self):
        items = [_make_item(days_ago=8)]
        result = _filter_by_date(items, recency_days=7)
        assert len(result) == 0

    def test_near_boundary_kept(self):
        items = [_make_item(days_ago=6)]
        result = _filter_by_date(items, recency_days=7)
        assert len(result) == 1


class TestRssEntryToItem:
    def test_hackernews_label(self):
        entry = MagicMock()
        entry.title = "HN Post"
        entry.link = "https://news.ycombinator.com/item?id=123"
        entry.summary = "summary"
        entry.published_parsed = None
        entry.updated_parsed = None
        item = _entry_to_item(entry, "hackernews")
        assert item["source"] == "hackernews"

    def test_missing_summary_falls_back_to_description(self):
        entry = MagicMock(spec=[])
        entry.title = "Post"
        entry.link = "https://example.com"
        entry.published_parsed = None
        entry.updated_parsed = None
        item = _entry_to_item(entry, "rss")
        assert item["body"] == ""

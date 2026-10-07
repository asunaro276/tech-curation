"""Unit tests for greedy topic grouping and representative selection."""
from __future__ import annotations

from unittest.mock import patch

from tech_curation.collect import grouping
from tech_curation.collect.grouping import Group, group_topic, is_japanese, representative_of


def _item(title: str, url: str = "", worth: float = 0.5, source: str = "zenn", primary: float = 0.0, body: str = "") -> dict:
    return {
        "title": title, "url": url or f"https://example.com/{title}", "source": source, "body": body,
        "worth": worth, "is_primary": primary, "topic": "Go",
    }


PAST = [{"date": "2026-10-06", "no": 2, "topic": "Go", "title": "Go 1.25 RC", "summary": "RC 版"}]


def _run(items, labels, past=(), past_urls=()):
    """labels: 記事タイトル → judge_group が返すラベル。呼ばれた記事のタイトルも返す。"""
    called = []

    def fake(item, seeds, past_groups, criteria):
        called.append(item["title"])
        return labels.get(item["title"])

    with patch.object(grouping, "judge_group", side_effect=fake):
        groups = group_topic(items, list(past), set(past_urls), "基準")
    return groups, called


class TestIsJapanese:
    def test_japanese_title(self):
        assert is_japanese(_item("Go 1.25 の新機能まとめ"))

    def test_english(self):
        assert not is_japanese(_item("Go 1.25 Release Notes", body="What's new in Go 1.25"))

    def test_kanji_only_is_not_enough(self):
        assert not is_japanese(_item("新機能 Go 1.25"))

    def test_japanese_body(self):
        assert is_japanese(_item("Go 1.25", body="Go 1.25 がリリースされました"))


class TestGroupTopic:
    def test_same_subject_joins_group(self):
        items = [_item("Go 1.25 まとめ", worth=0.9), _item("Go 1.25 Release Notes", worth=0.8)]
        groups, called = _run(items, {"Go 1.25 Release Notes": "g0"})
        assert len(groups) == 1
        assert [m["title"] for m in groups[0]["members"]] == ["Go 1.25 まとめ", "Go 1.25 Release Notes"]
        assert called == ["Go 1.25 Release Notes"]  # 最初の記事は判定しない

    def test_different_subjects_stay_separate(self):
        items = [_item("Go 1.25 まとめ", worth=0.9), _item("sqlc 入門", worth=0.8)]
        groups, _ = _run(items, {"sqlc 入門": "new"})
        assert len(groups) == 2

    def test_processed_in_worth_order(self):
        items = [_item("low", worth=0.1), _item("high", worth=0.9)]
        groups, called = _run(items, {"low": "new"})
        assert groups[0]["members"][0]["title"] == "high"
        assert called == ["low"]

    def test_reported_url_dropped_without_judgment(self):
        items = [_item("Go 1.25 まとめ", url="https://seen")]
        groups, called = _run(items, {}, past=PAST, past_urls={"https://seen"})
        assert groups == []
        assert called == []

    def test_same_as_past_is_dropped(self):
        groups, _ = _run([_item("Go 1.25 RC 解説")], {"Go 1.25 RC 解説": "same:p0"}, past=PAST)
        assert groups == []

    def test_follow_up_is_kept_with_reference(self):
        groups, _ = _run([_item("Go 1.25 正式リリース")], {"Go 1.25 正式リリース": "follow:p0"}, past=PAST)
        assert len(groups) == 1
        assert groups[0]["follow_of"] == {"date": "2026-10-06", "no": 2, "title": "Go 1.25 RC"}

    def test_first_article_is_judged_when_past_exists(self):
        _, called = _run([_item("Go 1.25 正式リリース")], {"Go 1.25 正式リリース": "new"}, past=PAST)
        assert called == ["Go 1.25 正式リリース"]

    def test_judgment_failure_creates_new_group(self):
        items = [_item("a", worth=0.9), _item("b", worth=0.8), _item("c", worth=0.7)]
        groups, _ = _run(items, {"b": None, "c": "g0"})
        assert [len(g["members"]) for g in groups] == [2, 1]


class TestRepresentative:
    def test_primary_wins_over_higher_worth(self):
        group = Group(members=[
            _item("Go 1.25 の新機能まとめ", worth=0.91),
            _item("Go 1.25 Release Notes", worth=0.80, primary=0.9),
        ], follow_of=None)
        rep = representative_of(group)
        assert rep["title"] == "Go 1.25 Release Notes"
        assert [r["title"] for r in rep["related"]] == ["Go 1.25 の新機能まとめ"]

    def test_japanese_wins_among_secondary(self):
        group = Group(members=[
            _item("Deep dive into Go 1.25", worth=0.85, source="rss"),
            _item("Go 1.25 の iter を試す", worth=0.70, source="qiita"),
        ], follow_of=None)
        assert representative_of(group)["title"] == "Go 1.25 の iter を試す"

    def test_github_source_is_primary(self):
        group = Group(members=[_item("解説記事", worth=0.9), _item("golang/go", worth=0.2, source="github")], follow_of=None)
        assert representative_of(group)["title"] == "golang/go"

    def test_follow_of_carried(self):
        ref = {"date": "2026-10-06", "no": 2, "title": "Go 1.25 RC"}
        rep = representative_of(Group(members=[_item("Go 1.25")], follow_of=ref))
        assert rep["follow_of"] == ref
        assert rep["related"] == []

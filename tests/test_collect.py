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


def _topic_item(title: str, url: str, source: str = "zenn", topic: str = "", body: str = "body") -> CollectedItem:
    item = _make_item(url)
    return {**item, "title": title, "source": source, "topic": topic, "body": body, "thumbnail": ""}


class TestMergeFilterJev:
    def _run(self, items, judge, topics=("Go", "Ruby", "トレンド"), threshold=0.5):
        from tech_curation.collect.nodes import merge_filter as mf

        config = AgentConfig(filter_threshold=threshold)
        state = {"config": config, "raw_items": items, "topics": list(topics)}
        with patch.object(mf, "judge_relevance_and_topic", side_effect=judge):
            return mf.merge_filter_node(state)["filtered_items"]

    def test_jev_topic_is_used(self):
        items = [_topic_item("iter パッケージ解説", "https://a.com", source="rss")]
        result = self._run(items, lambda item, topics, crit: (0.9, "Go"))
        assert result[0]["topic"] == "Go"
        assert result[0]["relevance_score"] == 0.9

    def test_jev_topic_takes_precedence_over_feed_hint(self):
        items = [_topic_item("Rails 8 へ上げる前に", "https://a.com", source="rss", topic="Ruby")]
        result = self._run(items, lambda item, topics, crit: (0.9, "Go"))
        assert result[0]["topic"] == "Go"

    def test_feed_hint_used_when_jev_fails(self):
        items = [_topic_item("Go と Ruby の比較", "https://a.com", source="rss", topic="Ruby")]
        result = self._run(items, lambda item, topics, crit: (0.5, None))
        assert result[0]["topic"] == "Ruby"

    def test_trend_is_not_filtered_by_relevance(self):
        items = [
            _topic_item("trend", "https://t.com", source="zenn"),
            _topic_item("go-low", "https://g.com", source="rss"),
        ]
        judged = {"trend": (0.05, "トレンド"), "go-low": (0.3, "Go")}
        result = self._run(items, lambda item, topics, crit: judged[item["title"]])
        assert [i["title"] for i in result] == ["trend"]

    def test_failure_falls_back_to_keyword_match_and_neutral(self):
        items = [_topic_item("Go 1.25 released", "https://a.com", source="rss")]
        result = self._run(items, lambda item, topics, crit: (0.5, None))
        assert result[0]["topic"] == "Go"
        assert result[0]["relevance_score"] == 0.5

    def test_below_threshold_excluded(self):
        items = [
            _topic_item("low", "https://a.com", source="rss"),
            _topic_item("high", "https://b.com", source="rss"),
        ]
        scores = {"low": 0.3, "high": 0.8}
        result = self._run(items, lambda item, topics, crit: (scores[item["title"]], "Go"))
        assert [i["title"] for i in result] == ["high"]

    def test_source_boost_applied(self):
        # zenn は +0.25 されるので 0.3 → 0.55 で閾値を超える
        items = [_topic_item("zenn 記事", "https://a.com", source="zenn")]
        result = self._run(items, lambda item, topics, crit: (0.3, "Go"))
        assert result[0]["relevance_score"] == 0.55


class TestSelectJev:
    EMPTY_HISTORY = {"groups_by_topic": {}, "urls": set()}

    def _run(self, items, worth, quotas=None, default_quota=2, group=lambda item, seeds, past, crit: "new",
             history=None, release=lambda item: 0.9):
        from tech_curation.collect import grouping
        from tech_curation.collect.nodes import select as sel
        from tech_curation.jev import Selection

        config = AgentConfig(topic_quotas=quotas or {}, default_topic_quota=default_quota)
        judge = lambda item, crit, policy="": Selection(worth(item, crit), release(item), 0.0)
        with patch.object(sel, "judge_selection", side_effect=judge), \
                patch.object(sel, "_load_policy", return_value=""), \
                patch.object(grouping, "judge_group", side_effect=lambda *a: (group(*a), 0.9)), \
                patch.object(grouping, "judge_same_subject", return_value=1.0), \
                patch.object(sel, "_load_history", return_value=history or self.EMPTY_HISTORY):
            return sel.select_node({"config": config, "filtered_items": items})["filtered_items"]

    def test_quota_enforced_by_worth(self):
        items = [_topic_item(f"go{i}", f"https://go{i}.com", topic="Go") for i in range(4)]
        worths = {"go0": 0.2, "go1": 0.9, "go2": 0.5, "go3": 0.7}
        result = self._run(items, lambda item, crit: worths[item["title"]], quotas={"Go": 1})
        assert [i["title"] for i in result] == ["go1"]

    def test_unlisted_topic_uses_default(self):
        items = [_topic_item(f"rb{i}", f"https://rb{i}.com", topic="Ruby") for i in range(4)]
        result = self._run(items, lambda item, crit: 0.8, quotas={"Go": 1}, default_quota=3)
        assert len(result) == 3

    def test_low_worth_topic_keeps_one(self):
        items = [
            _topic_item("rb-low", "https://a.com", topic="Ruby"),
            _topic_item("rb-lower", "https://b.com", topic="Ruby"),
        ]
        worths = {"rb-low": 0.15, "rb-lower": 0.05}
        result = self._run(items, lambda item, crit: worths[item["title"]], quotas={"Ruby": 1})
        assert [i["title"] for i in result] == ["rb-low"]

    def test_empty_input(self):
        assert self._run([], lambda item, crit: 0.5) == []

    def test_related_articles_do_not_consume_quota(self):
        items = [_topic_item(f"c{i}", f"https://c{i}.com", topic="Claude") for i in range(4)]
        worths = {"c0": 0.9, "c1": 0.8, "c2": 0.7, "c3": 0.6}
        groups = {"c1": "g0", "c2": "g0", "c3": "new"}
        result = self._run(items, lambda item, crit: worths[item["title"]], quotas={"Claude": 2},
                           group=lambda item, seeds, past, crit: groups[item["title"]])
        assert [r["title"] for r in result] == ["c0", "c3"]
        assert [r["title"] for r in result[0]["related"]] == ["c1", "c2"]

    def test_grouping_is_per_topic(self):
        items = [_topic_item("go", "https://go.com", topic="Go"), _topic_item("rb", "https://rb.com", topic="Ruby")]
        seen_seeds = []

        def group(item, seeds, past, crit):
            seen_seeds.append([s["title"] for s in seeds])
            return "g0"

        result = self._run(items, lambda item, crit: 0.8, group=group)
        assert len(result) == 2
        assert seen_seeds == []  # 各トピック1本目で過去もないので判定は呼ばれない

    def test_past_url_and_same_topic_dropped(self):
        items = [
            _topic_item("seen", "https://seen.com", topic="Go"),
            _topic_item("again", "https://again.com", topic="Go"),
        ]
        history = {
            "groups_by_topic": {"Go": [{"date": "2026-10-06", "no": 1, "topic": "Go", "title": "Go 1.25", "summary": ""}]},
            "urls": {"https://seen.com"},
        }
        result = self._run(items, lambda item, crit: 0.8, history=history,
                           group=lambda item, seeds, past, crit: "same:p0")
        assert result == []

    def test_trend_articles_are_never_grouped(self):
        items = [_topic_item(f"t{i}", f"https://t{i}.com", topic="Claude") for i in range(3)]
        called = []
        result = self._run(items, lambda item, crit: 0.8, default_quota=5, release=lambda item: 0.1,
                           group=lambda item, seeds, past, crit: called.append(item["title"]) or "g0")
        assert len(result) == 3
        assert all(r["related"] == [] for r in result)
        assert called == []  # トレンド情報はグループ判定を呼ばない

    def test_releases_and_trends_share_quota_by_worth(self):
        items = [
            _topic_item("rel-a", "https://a.com", topic="Go"),
            _topic_item("rel-b", "https://b.com", topic="Go"),
            _topic_item("trend", "https://c.com", topic="Go"),
        ]
        worths = {"rel-a": 0.6, "rel-b": 0.5, "trend": 0.9}
        result = self._run(items, lambda item, crit: worths[item["title"]], quotas={"Go": 2},
                           release=lambda item: 0.1 if item["title"] == "trend" else 0.9,
                           group=lambda item, seeds, past, crit: "g0")
        assert [r["title"] for r in result] == ["trend", "rel-a"]
        assert [r["title"] for r in result[1]["related"]] == ["rel-b"]

    def test_reported_url_dropped_for_trend_too(self):
        items = [_topic_item("seen-trend", "https://seen.com", topic="Go")]
        history = {"groups_by_topic": {}, "urls": {"https://seen.com"}}
        assert self._run(items, lambda item, crit: 0.8, history=history, release=lambda item: 0.1) == []

    def test_all_judgments_fail(self):
        from tech_curation import jev
        from tech_curation.collect.nodes import select as sel

        items = [_topic_item(f"go{i}", f"https://go{i}.com", topic="Go") for i in range(3)] + [
            _topic_item("rb0", "https://rb0.com", topic="Ruby")
        ]
        config = AgentConfig(topic_quotas={"Go": 2, "Ruby": 1})
        with patch.object(jev, "_client", side_effect=RuntimeError("service down")), \
                patch.object(sel, "_load_policy", return_value=""), \
                patch.object(sel, "_load_history", return_value=self.EMPTY_HISTORY):
            result = sel.select_node({"config": config, "filtered_items": items})["filtered_items"]
        assert [i["title"] for i in result] == ["go0", "go1", "rb0"]


class TestCandidateSlots:
    def test_widened_to_three_times_quota(self):
        from tech_curation.collect.nodes.merge_filter import candidate_slots

        config = AgentConfig(topic_quotas={"Claude": 3, "Go": 1})
        assert candidate_slots("Claude", 4, config) == 9
        assert candidate_slots("Go", 4, config) == 4  # 現行の枠のほうが大きければそのまま

    def test_bucket_uses_widened_slots(self):
        from tech_curation.collect.nodes import merge_filter as mf

        items = [_topic_item(f"c{i}", f"https://c{i}.com", source="rss", topic="Claude") for i in range(10)]
        config = AgentConfig(topic_quotas={"Claude": 3}, max_items_per_run=8)
        state = {"config": config, "raw_items": items, "topics": ["Claude", "Go"]}
        with patch.object(mf, "judge_relevance_and_topic", return_value=(0.9, "Claude")):
            result = mf.merge_filter_node(state)["filtered_items"]
        assert len(result) == 9  # 現行の枠は ceil(8/2)=4 だが 3×3=9 まで渡す


class TestGroupSummary:
    def _group(self, n_related: int) -> dict:
        rep = _topic_item("Go 1.25 Release Notes", "https://go.dev", source="rss", topic="Go", body="R" * 3000)
        related = [_topic_item(f"rel{i}", f"https://r{i}.com", topic="Go", body=f"{i}" * 3000) for i in range(n_related)]
        return {**rep, "related": related}

    def test_single_article_request_unchanged(self):
        from tech_curation.collect.nodes.summarize_format import summary_request

        content, max_tokens = summary_request(self._group(0), "要約して")
        assert content == "要約して\n\nArticle:\nTitle: Go 1.25 Release Notes\n\n" + "R" * 1000
        assert max_tokens == 256

    def test_group_request_limits_bodies_and_count(self):
        from tech_curation.collect.nodes.summarize_format import summary_request

        content, max_tokens = summary_request(self._group(6), "要約して")
        assert max_tokens == 512
        assert "R" * 1500 in content and "R" * 1501 not in content
        assert "0" * 500 in content and "0" * 501 not in content
        assert "## 関連記事 4" in content and "## 関連記事 5" not in content
        assert "1本の要約にまとめて" in content

    def test_revise_removes_whole_group(self):
        from tech_curation.collect.nodes.revise import revise_node

        groups = [self._group(2), {**self._group(0), "title": "other"}]
        state = {
            "formatted_items": groups,
            "review_issues": [{"item_index": 0, "action": "remove", "reason": "", "rewrite_hint": ""}],
            "config": AgentConfig(),
            "topics": ["Go"],
        }
        result = revise_node(state)["formatted_items"]
        assert [g["title"] for g in result] == ["other"]

    def test_revise_rewrites_with_group_input(self):
        from tech_curation.collect.nodes import revise

        state = {
            "formatted_items": [self._group(2)],
            "review_issues": [{"item_index": 0, "action": "rewrite", "reason": "", "rewrite_hint": "短く"}],
            "config": AgentConfig(),
            "topics": ["Go"],
        }
        with patch.object(revise, "chat", return_value="新しい要約") as chat:
            result = revise.revise_node(state)["formatted_items"]
        assert result[0]["summary"] == "新しい要約"
        assert result[0]["related"] == state["formatted_items"][0]["related"]
        sent = chat.call_args.args[0][0]["content"]
        assert "改善指示: 短く" in sent and "## 関連記事 2" in sent


RSS_XML = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Go 1.25 released</title><link>https://go.dev/blog/go1.25</link><description>d</description></item>
</channel></rss>"""


class TestParallelFetch:
    def test_fetch_feed_uses_timeout_and_parses(self):
        import httpx

        from tech_curation.collect.nodes import rss

        def fake_get(url, **kwargs):
            assert kwargs["timeout"] == rss.FEED_TIMEOUT
            return httpx.Response(200, content=RSS_XML, request=httpx.Request("GET", url))

        with patch.object(rss.httpx, "get", side_effect=fake_get):
            items = rss._fetch_feed("https://zenn.dev/topics/go/feed")
        assert [(i["title"], i["source"], i["topic"]) for i in items] == [("Go 1.25 released", "zenn", "Go")]

    def test_rss_node_keeps_feed_order_and_records_errors(self, tmp_path, monkeypatch):
        from tech_curation.collect.nodes import rss

        feeds = tmp_path / "agent-config" / "feeds.md"
        feeds.parent.mkdir(parents=True)
        feeds.write_text("## アクティブ\n- https://a.example/feed\n- https://slow.example/feed\n- https://b.example/feed\n")
        monkeypatch.setenv("VAULT_ROOT", str(tmp_path))

        def fake_fetch(url, hint=""):
            if "slow" in url:
                raise TimeoutError("timed out")
            return [_topic_item(url, url)]

        with patch.object(rss, "_fetch_feed", side_effect=fake_fetch):
            result = rss.rss_node({"config": AgentConfig()})
        assert [i["url"] for i in result["raw_items"]] == ["https://a.example/feed", "https://b.example/feed"]
        assert result["errors"] == ["rss:https://slow.example/feed:timed out"]

    def test_plan_generates_queries_per_topic(self, tmp_path, monkeypatch):
        from tech_curation.collect.nodes import plan

        topics = tmp_path / "agent-config" / "topics.md"
        topics.parent.mkdir(parents=True)
        topics.write_text("## アクティブ\n- Go\n- Ruby\n- vue\n")
        monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
        with patch.object(plan, "_generate_queries", side_effect=lambda t, p, pol="": [f"{t} q"]):
            result = plan.plan_node({"config": AgentConfig(), "topics": []})
        assert result["queries"] == {"Go": ["Go q"], "Ruby": ["Ruby q"], "vue": ["vue q"]}

    def test_timed_node_logs_duration(self, capsys):
        from tech_curation.collect.graph import _timed

        assert _timed("plan", lambda s: {"x": 1})({}) == {"x": 1}
        assert "[time] plan " in capsys.readouterr().out


class TestFeedsMd:
    def test_parses_hint_and_max(self):
        from tech_curation.collect.nodes.rss import _parse_feeds_md

        md = (
            "## アクティブ\n"
            "- https://rubyweekly.com/rss/ [Ruby]\n"
            "- https://yamadashy.github.io/tech-blog-rss-feed/feeds/rss.xml {max=50}\n"
            "- https://zenn.dev/topics/go/feed [Go] {max=20}\n"
            "- https://www.publickey1.jp/atom.xml\n"
            "## 停止中\n- https://stopped.example/feed\n"
        )
        assert _parse_feeds_md(md) == [
            ("https://rubyweekly.com/rss/", "Ruby", None),
            ("https://yamadashy.github.io/tech-blog-rss-feed/feeds/rss.xml", "", 50),
            ("https://zenn.dev/topics/go/feed", "Go", 20),
            ("https://www.publickey1.jp/atom.xml", "", None),
        ]

    def test_max_overrides_weighted_default(self, tmp_path, monkeypatch):
        from tech_curation.collect.nodes import rss

        feeds = tmp_path / "agent-config" / "feeds.md"
        feeds.parent.mkdir(parents=True)
        feeds.write_text("## アクティブ\n- https://agg.example/feed {max=50}\n- https://small.example/feed\n")
        monkeypatch.setenv("VAULT_ROOT", str(tmp_path))
        many = lambda url, hint="": [_topic_item(f"{url}#{i}", f"{url}#{i}") for i in range(80)]
        with patch.object(rss, "_fetch_feed", side_effect=many):
            items = rss.rss_node({"config": AgentConfig()})["raw_items"]
        counts = {u: sum(i["url"].startswith(u) for i in items) for u in ("https://agg", "https://small")}
        assert counts["https://agg"] == 50
        assert counts["https://small"] == 18  # 既定: フィードが少ないので基本30件 × rss の重み 0.6


class TestTrendBucket:
    def _run(self, items, judged):
        from tech_curation.collect.nodes import merge_filter as mf

        state = {"config": AgentConfig(), "raw_items": items, "topics": ["Go", "トレンド"]}
        with patch.object(mf, "judge_relevance_and_topic", side_effect=lambda item, t, c: judged[item["title"]]):
            return mf.merge_filter_node(state)["filtered_items"]

    def test_non_github_sources_enter_trend(self):
        items = [
            _topic_item("企業ブログ", "https://tech.example.com/a", source="rss"),
            _topic_item("Publickey", "https://www.publickey1.jp/a", source="rss"),
            _topic_item("owner/repo", "https://github.com/owner/repo", source="github"),
        ]
        judged = {t["title"]: (0.05, "トレンド") for t in items}
        result = self._run(items, judged)
        assert sorted(i["title"] for i in result) == ["Publickey", "企業ブログ"]

    def test_trend_gets_wider_candidate_slots(self):
        from tech_curation.collect.nodes.merge_filter import candidate_slots

        config = AgentConfig(topic_quotas={"トレンド": 5, "Go": 1})
        assert candidate_slots("トレンド", 4, config) == 30
        assert candidate_slots("Go", 4, config) == 4


class TestSecurityTopic:
    def test_japanese_keyword_matches_inside_sentence(self):
        from tech_curation.collect.nodes.merge_filter import _assign_topic

        item = _topic_item("OpenSSLに深刻な脆弱性、修正版が公開", "https://gihyo.jp/news/1", source="gihyo")
        assert _assign_topic(item, ["Go", "セキュリティ", "トレンド"]) == "セキュリティ"

    def test_ascii_keyword_keeps_word_boundary(self):
        from tech_curation.collect.nodes.merge_filter import _assign_topic

        item = _topic_item("CVE-2026-1234 in libfoo", "https://a.example/1")
        assert _assign_topic(item, ["セキュリティ", "トレンド"]) == "セキュリティ"
        unrelated = _topic_item("Insecurely fast builds", "https://a.example/2")
        assert _assign_topic(unrelated, ["セキュリティ", "トレンド"]) == "トレンド"

    def test_default_quota(self):
        assert AgentConfig().quota_for("セキュリティ") == 3

    def test_gihyo_source_label(self):
        from tech_curation.collect.nodes.rss import _source_label

        assert _source_label("https://gihyo.jp/feed/rss2") == "gihyo"

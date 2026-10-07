"""Unit tests for grouped Markdown report generation."""
from __future__ import annotations

from tech_curation.feedback.parser import extract_source_from_section, parse_feedback
from tech_curation.obsidian.records import build_daily_record
from tech_curation.obsidian.report import generate_daily_report, number_items


def _item(title: str, url: str, source: str = "zenn", **extra) -> dict:
    return {
        "title": title, "url": url, "source": source, "published": "2026-10-06T00:00:00Z",
        "summary": f"{title} の要約", "content_type": "trend", "thumbnail": "", "body": "", **extra,
    }


ITEMS = {
    "Go": [
        _item("Go 1.25 Release Notes", "https://go.dev/1.25", source="rss",
              related=[_item("Go 1.25 まとめ", "https://zenn.dev/go125"), _item("iter を試す", "https://qiita.com/iter", source="qiita")]),
        _item("Go 1.25 正式リリース", "https://go.dev/ga", source="rss",
              follow_of={"date": "2026-10-01", "no": 2, "title": "Go 1.25 RC"}),
    ],
    "Ruby": [],
    "Claude": [_item("Claude Code の新機能", "https://zenn.dev/cc")],
}


def _report() -> str:
    return generate_daily_report(ITEMS, date_str="2026-10-06")[1]


class TestGroupedReport:
    def test_sections_are_numbered_across_topics(self):
        md = _report()
        assert "### #1 [Go 1.25 Release Notes](https://go.dev/1.25)" in md
        assert "### #2 [Go 1.25 正式リリース](https://go.dev/ga)" in md
        assert "### #3 [Claude Code の新機能](https://zenn.dev/cc)" in md
        assert "## Ruby" not in md

    def test_group_lists_all_links(self):
        md = _report()
        assert "- [Go 1.25 Release Notes](https://go.dev/1.25) — rss\n- [Go 1.25 まとめ](https://zenn.dev/go125) — zenn\n" in md
        assert "- [iter を試す](https://qiita.com/iter) — qiita" in md

    def test_single_article_group_has_one_link(self):
        section = _report().split("### #3")[1]
        assert section.count("](https://") == 2  # 見出しのリンクと一覧の1件
        assert "- [Claude Code の新機能](https://zenn.dev/cc) — zenn" in section

    def test_follow_up_links_previous_report(self):
        md = _report()
        assert "📎 続報: [[tech-curation/2026-10-01/daily|2026-10-01]] の「Go 1.25 RC」" in md

    def test_feedback_comment_has_dup_field(self):
        md = _report()
        assert md.count("<!-- fb: relevance=, dup=, comment= -->") == 3
        assert parse_feedback(md) == []  # 未記入はフィードバックなし

    def test_source_labels_still_extracted(self):
        assert extract_source_from_section(_report()) == ["rss", "rss", "zenn"]

    def test_record_numbering_matches_report(self):
        md = _report()
        record = build_daily_record("2026-10-06", number_items(ITEMS))
        for group in record["groups"]:
            assert f"### #{group['no']} [{group['title']}]" in md
        assert record["groups"][1]["follow_of"]["title"] == "Go 1.25 RC"

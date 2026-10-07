"""Unit tests for the self-improvement pipeline."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tech_curation.feedback.parser import FeedbackItem, parse_feedback
from tech_curation.improve.nodes.analyze_patterns import _compute_source_stats
from tech_curation.improve.nodes.apply_changes import _update_note_status, _append_feedback_history
from tech_curation.config.settings import AgentConfig, load_config, update_config


class TestFeedbackParser:
    def test_parses_filled_comment(self):
        md = "<!-- fb: relevance=4, comment=参考になった -->"
        items = parse_feedback(md)
        assert len(items) == 1
        assert items[0]["relevance"] == 4
        assert items[0]["comment"] == "参考になった"

    def test_skips_empty_comment(self):
        md = "<!-- fb: relevance=, comment= -->"
        items = parse_feedback(md)
        assert items == []

    def test_mixed_filled_and_empty(self):
        md = "<!-- fb: relevance=3, comment=good -->\n<!-- fb: relevance=, comment= -->"
        items = parse_feedback(md)
        assert len(items) == 1
        assert items[0]["relevance"] == 3

    def test_multiple_items(self):
        md = (
            "<!-- fb: relevance=5, comment=excellent -->\n"
            "<!-- fb: relevance=2, comment=not relevant -->"
        )
        items = parse_feedback(md)
        assert len(items) == 2
        assert items[0]["item_index"] == 0
        assert items[1]["item_index"] == 1


class TestComputeSourceStats:
    def test_per_source_average(self):
        feedback = [
            FeedbackItem(item_index=0, relevance=5, comment=""),
            FeedbackItem(item_index=1, relevance=1, comment=""),
        ]
        sources = ["github", "hackernews"]
        stats = _compute_source_stats(feedback, sources)
        stats_map = {s["source"]: s["avg_relevance"] for s in stats}
        assert stats_map["github"] == 5.0
        assert stats_map["hackernews"] == 1.0

    def test_skips_none_relevance(self):
        feedback = [FeedbackItem(item_index=0, relevance=None, comment="good")]
        sources = ["rss"]
        stats = _compute_source_stats(feedback, sources)
        assert stats == []


class TestUpdateNoteStatus:
    def test_draft_becomes_submitted(self):
        content = "---\nstatus: draft\n---\n\n# Title"
        updated = _update_note_status(content)
        assert "status: submitted" in updated
        assert "status: draft" not in updated


class TestFeedbackHistory:
    def test_appends_entry(self, tmp_path):
        history_path = tmp_path / "feedback-history.json"
        _append_feedback_history(
            history_path,
            note_path="tech-curation/2026-06-21-test.md",
            feedback_items=[{"item_index": 0, "relevance": 4, "comment": "good"}],
            reason="HN avg low",
            date="2026-06-21",
        )
        data = json.loads(history_path.read_text())
        assert len(data) == 1
        assert data[0]["note_path"] == "tech-curation/2026-06-21-test.md"

    def test_appends_to_existing(self, tmp_path):
        history_path = tmp_path / "feedback-history.json"
        history_path.write_text(json.dumps([{"existing": True}]))
        _append_feedback_history(history_path, "path", [], "reason", "2026-06-21")
        data = json.loads(history_path.read_text())
        assert len(data) == 2


class TestConfigLoadUpdate:
    def test_load_defaults(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text(
            "## source_weights\n- github: 0.9\n- hackernews: 0.3\n\n"
            "filter_threshold: 0.6\nrecency_days: 14\n"
        )
        cfg = load_config(prompts)
        assert cfg.source_weights["github"] == 0.9
        assert cfg.source_weights["hackernews"] == 0.3
        assert cfg.filter_threshold == 0.6
        assert cfg.recency_days == 14

    def test_update_weight(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text("## source_weights\n- hackernews: 0.5\n")
        update_config(prompts, {"source_weights.hackernews": 0.2}, None, "HN low", "2026-06-21")
        text = prompts.read_text()
        assert "hackernews: 0.2" in text


class TestJevConfig:
    def test_defaults_when_sections_missing(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text("filter_threshold: 0.5\n")
        cfg = load_config(prompts)
        assert cfg.relevance_criteria == AgentConfig().relevance_criteria
        assert cfg.worth_criteria == AgentConfig().worth_criteria
        assert cfg.quota_for("Go") == 1
        assert cfg.quota_for("unknown topic") == cfg.default_topic_quota

    def test_loads_criteria_and_quotas(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text(
            "## relevance_criteria\n- 0: 無関係\n- 1: 関係あり\n\n"
            "## worth_criteria\n入門記事は no。\n\n"
            "## topic_quotas\n- Go: 2\n- Ruby on Rails: 4\n- default: 3\n"
        )
        cfg = load_config(prompts)
        assert cfg.relevance_criteria == "- 0: 無関係\n- 1: 関係あり"
        assert cfg.worth_criteria == "入門記事は no。"
        assert cfg.quota_for("go") == 2
        assert cfg.quota_for("Ruby on Rails") == 4
        assert cfg.quota_for("unknown topic") == 3

    def test_quota_is_at_least_one(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text("## topic_quotas\n- Go: 0\n")
        assert load_config(prompts).quota_for("Go") == 1

    def test_repo_prompts_md_matches_defaults(self):
        cfg = load_config(Path(__file__).parent.parent / "vault" / "agent-config" / "prompts.md")
        defaults = AgentConfig()
        assert cfg.relevance_criteria == defaults.relevance_criteria
        assert cfg.worth_criteria == defaults.worth_criteria
        assert cfg.topic_quotas == defaults.topic_quotas
        assert cfg.default_topic_quota == defaults.default_topic_quota

    def test_update_existing_topic_quota(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text("## topic_quotas\n\n- Go: 1\n- Ruby: 2\n\n## 改善履歴\n")
        update_config(prompts, {"topic_quotas.Go": 2}, None, "Go を増やす", "2026-10-07")
        cfg = load_config(prompts)
        assert cfg.quota_for("Go") == 2
        assert cfg.quota_for("Ruby") == 2

    def test_add_new_topic_quota(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text("## topic_quotas\n\n- Go: 1\n\n## 改善履歴\n")
        update_config(prompts, {"topic_quotas.Rust": 3}, None, "Rust 追加", "2026-10-07")
        cfg = load_config(prompts)
        assert cfg.quota_for("Rust") == 3
        assert cfg.quota_for("Go") == 1

    def test_rewrite_worth_criteria(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text("## worth_criteria\n\n旧基準\n\n## 改善履歴\n")
        update_config(prompts, None, {"worth_criteria": r"入門記事は no。\d のような記号も保持"}, "入門不要", "2026-10-07")
        assert load_config(prompts).worth_criteria == r"入門記事は no。\d のような記号も保持"

    def test_missing_criteria_section_is_added(self, tmp_path):
        prompts = tmp_path / "prompts.md"
        prompts.write_text("## summarize_prompt\n\n要約して\n\n## 改善履歴\n")
        update_config(prompts, None, {"relevance_criteria": "- 0: 無関係\n- 1: 関係あり"}, "基準追加", "2026-10-07")
        cfg = load_config(prompts)
        assert cfg.relevance_criteria == "- 0: 無関係\n- 1: 関係あり"
        assert cfg.summarize_prompt == "要約して"

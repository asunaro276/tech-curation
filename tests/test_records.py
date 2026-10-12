"""Unit tests for daily group records."""
from __future__ import annotations

import json
from datetime import date

from tech_curation.obsidian.records import build_daily_record, load_past_history, record_path


def _item(title: str, url: str, **extra) -> dict:
    return {"title": title, "url": url, "source": "zenn", "summary": f"{title} の要約", **extra}


def _write(vault, date_str, record):
    path = vault / record_path(date_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record if isinstance(record, str) else json.dumps(record), encoding="utf-8")


class TestBuildDailyRecord:
    def test_groups_include_related_articles(self):
        rep = _item("Go 1.25 Release Notes", "https://go.dev/1.25", is_primary=0.9,
                    related=[_item("Go 1.25 まとめ", "https://zenn.dev/x")])
        record = build_daily_record("2026-10-06", [(3, "Go", rep)])
        group = record["groups"][0]
        assert group["no"] == 3
        assert group["topic"] == "Go"
        assert [a["url"] for a in group["articles"]] == ["https://go.dev/1.25", "https://zenn.dev/x"]
        assert group["articles"][0]["primary"] is True
        assert group["follow_of"] is None


class TestLoadPastHistory:
    def test_reads_past_days_and_skips_today(self, tmp_path):
        today = date(2026, 10, 7)
        _write(tmp_path, "2026-10-06", build_daily_record("2026-10-06", [(1, "Go", _item("Go 1.25 RC", "https://a"))]))
        _write(tmp_path, "2026-10-07", build_daily_record("2026-10-07", [(1, "Go", _item("today", "https://t"))]))
        history = load_past_history(tmp_path, today, 7)
        assert [g["title"] for g in history["groups_by_topic"]["Go"]] == ["Go 1.25 RC"]
        assert history["urls"] == {"https://a"}

    def test_respects_day_window(self, tmp_path):
        _write(tmp_path, "2026-09-20", build_daily_record("2026-09-20", [(1, "Go", _item("old", "https://old"))]))
        history = load_past_history(tmp_path, date(2026, 10, 7), 7)
        assert history["groups_by_topic"] == {}
        assert history["urls"] == set()

    def test_missing_and_broken_files_are_skipped(self, tmp_path):
        _write(tmp_path, "2026-10-05", "{not json")
        _write(tmp_path, "2026-10-04", {"groups": "oops"})
        _write(tmp_path, "2026-10-03", build_daily_record("2026-10-03", [(2, "Ruby", _item("Ruby 3.5", "https://r"))]))
        history = load_past_history(tmp_path, date(2026, 10, 7), 7)
        assert history["groups_by_topic"]["Ruby"][0]["no"] == 2
        assert history["urls"] == {"https://r"}

    def test_no_records(self, tmp_path):
        history = load_past_history(tmp_path, date(2026, 10, 7), 7)
        assert history == {"groups_by_topic": {}, "urls": set()}


def test_typesafe_key_loaded_from_parameter_store(tmp_path, monkeypatch):
    import os
    from unittest.mock import patch

    from tech_curation.obsidian import sync

    (tmp_path / sync._SETUP_SENTINEL).touch()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    creds = {"auth_token": "t", "vault_name": "v", "typesafe_api_key": "ts-key"}
    with patch.object(sync, "_load_ob_credentials_from_parameter_store", return_value=creds):
        sync.setup_ob_credentials(tmp_path)
    assert os.environ["TYPESAFE_API_KEY"] == "ts-key"

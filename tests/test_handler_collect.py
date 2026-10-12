"""Handler test: report and items.json are written together."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import handler_collect


def test_report_and_record_written(tmp_path):
    item = {
        "title": "Go 1.25", "url": "https://go.dev", "source": "rss", "published": "2026-10-06",
        "summary": "要約", "content_type": "trend", "thumbnail": "", "body": "", "topic": "Go", "related": [],
    }
    app = MagicMock()
    app.invoke.return_value = {"topics": ["Go"], "formatted_items": [item], "errors": []}
    pushed = []
    with patch.object(handler_collect, "VAULT_ROOT", tmp_path), \
            patch.object(handler_collect, "setup_ob_credentials"), \
            patch.object(handler_collect, "ob_sync_pull"), \
            patch.object(handler_collect, "ob_sync_push", side_effect=lambda root: pushed.append(sorted(p.name for p in root.rglob("*")))), \
            patch.object(handler_collect, "get_collect_app", return_value=app):
        result = handler_collect.handler({}, None)

    filename = json.loads(result["body"])["file_written"]
    day_dir = (tmp_path / filename).parent
    record = json.loads((day_dir / "items.json").read_text(encoding="utf-8"))
    assert record["groups"][0]["no"] == 1
    assert "### #1 [Go 1.25]" in (tmp_path / filename).read_text(encoding="utf-8")
    assert "items.json" in pushed[0]  # push の時点で記録が書かれている

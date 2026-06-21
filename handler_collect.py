"""Lambda entry point for the information collection pipeline."""
from __future__ import annotations

import json
import os
from pathlib import Path

from tech_curation.collect.graph import get_collect_app
from tech_curation.collect.state import CollectState
from tech_curation.config.settings import AgentConfig, load_config
from tech_curation.obsidian.report import generate_daily_report
from tech_curation.obsidian.sync import ob_sync_pull, ob_sync_push, setup_ob_credentials, write_vault_file

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL", "")


def handler(event: dict, context) -> dict:
    setup_ob_credentials(VAULT_ROOT)
    ob_sync_pull(VAULT_ROOT)

    prompts_path = VAULT_ROOT / "agent-config" / "prompts.md"
    if prompts_path.exists():
        config = load_config(prompts_path)
    else:
        config = AgentConfig()

    initial_state = CollectState(
        topics=[],
        config=config,
        queries={},
        raw_items=[],
        filtered_items=[],
        formatted_items=[],
        review_issues=[],
        review_iterations=0,
        errors=[],
    )

    app = get_collect_app()
    final_state = app.invoke(initial_state)

    topics = final_state.get("topics", [])
    formatted_items = final_state.get("formatted_items", [])

    # トピックごとに振り分け（順序を保持）
    items_by_topic: dict[str, list] = {t: [] for t in topics}
    for item in formatted_items:
        placed = False
        for t in topics:
            if t.lower() in item.get("title", "").lower() or t.lower() in item.get("body", "").lower():
                items_by_topic[t].append(item)
                placed = True
                break
        if not placed and topics:
            items_by_topic[topics[0]].append(item)

    filename, content = generate_daily_report(
        items_by_topic,
        api_gateway_url=API_GATEWAY_URL,
    )
    write_vault_file(VAULT_ROOT, filename, content)

    ob_sync_push(VAULT_ROOT)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "file_written": filename,
            "items_collected": len(formatted_items),
            "errors": final_state.get("errors", []),
        }),
    }

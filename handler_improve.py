"""Lambda entry point for the self-improvement pipeline."""
from __future__ import annotations

import json
import os
from pathlib import Path

import boto3

from tech_curation.improve.graph import get_improve_app
from tech_curation.improve.state import ImproveState
from tech_curation.obsidian.sync import ob_sync_pull, ob_sync_push, setup_ob_credentials

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "vault")))


def _run_pipeline(note_path: str) -> None:
    setup_ob_credentials(VAULT_ROOT)
    ob_sync_pull(VAULT_ROOT)

    initial_state = ImproveState(
        note_path=note_path,
        note_content="",
        feedback_items=[],
        overall_feedback="",
        policy="",
        source_labels=[],
        source_stats=[],
        qualitative_analysis="",
        change_proposal=None,
        proposal_review_issues=[],
        proposal_review_iterations=0,
        errors=[],
    )

    app = get_improve_app()
    app.invoke(initial_state)
    ob_sync_push(VAULT_ROOT)


def handler(event: dict, context) -> dict:
    # Async processing invocation (from self-invoke below)
    if event.get("_process"):
        _run_pipeline(event["note_path"])
        return {}

    # HTTP request from API Gateway
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")

    if method == "GET":
        note_path = (event.get("queryStringParameters") or {}).get("note_path", "")
    else:
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)
        note_path = body.get("note_path", "")

    if not note_path:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "note_path is required"}),
        }

    # Token validation
    api_token = os.environ.get("API_TOKEN", "")
    if api_token:
        params = event.get("queryStringParameters") or {}
        body_token = ""
        if method == "POST":
            try:
                body_token = json.loads(event.get("body", "{}")).get("token", "")
            except Exception:
                pass
        supplied = params.get("token", "") or body_token
        if supplied != api_token:
            return {"statusCode": 403, "body": json.dumps({"error": "forbidden"})}

    # Fire-and-forget: invoke self asynchronously so API GW gets a fast response
    boto3.client("lambda", region_name=os.environ.get("AWS_REGION", "ap-northeast-1")).invoke(
        FunctionName=context.function_name,
        InvocationType="Event",
        Payload=json.dumps({"_process": True, "note_path": note_path}).encode(),
    )

    if method == "GET":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html; charset=utf-8"},
            "body": (
                "<html><body style='font-family:sans-serif;padding:2em'>"
                "<h2>✅ 受け付けました</h2>"
                "<p>フィードバックを処理中です。数分後に反映されます。</p>"
                f"<p><small>{note_path}</small></p>"
                "</body></html>"
            ),
        }

    return {
        "statusCode": 202,
        "body": json.dumps({"note_path": note_path, "status": "accepted"}),
    }

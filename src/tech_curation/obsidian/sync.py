"""ob sync push/pull wrappers and Secrets Manager credential injection."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

_SETUP_SENTINEL = ".ob-setup-done"

# Lambda の $HOME (/home/sbx_user1051) は読み取り専用。ob CLI が使う設定ファイルを
# /tmp に向けるために HOME を上書きする。
if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ.setdefault("HOME", "/tmp")


def _load_ob_credentials_from_secrets_manager(secret_name: str) -> dict:
    import boto3

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def setup_ob_credentials(vault_root: Path) -> None:
    """Read auth_token + vault_name from Secrets Manager and configure ob for Lambda.

    Secrets Manager の値は以下の JSON 形式:
      {
        "auth_token": "<~/.config/obsidian-headless/auth_token の内容>",
        "vault_name": "My Vault",
        "vault_password": ""   // E2E暗号化vaultの場合のみ
      }

    Lambda の /tmp は warm start で共有されるため、ob sync-setup はセンチネルファイルで
    コールドスタート時のみ実行する。
    """
    secret_name = os.environ.get("OB_CREDENTIALS_SECRET", "tech-curation/ob-credentials")
    if not secret_name:
        return
    try:
        creds = _load_ob_credentials_from_secrets_manager(secret_name)

        # obsidian-headless の認証トークンを書き込む
        config_dir = Path.home() / ".config" / "obsidian-headless"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "auth_token").write_text(creds["auth_token"], encoding="utf-8")

        # DeepSeek API キーを環境変数に設定（Secrets Manager に格納）
        if creds.get("deepseek_api_key"):
            os.environ["DEEPSEEK_API_KEY"] = creds["deepseek_api_key"]

        # GitHub API トークン（任意: 未設定時は匿名 60req/h）
        if creds.get("github_token"):
            os.environ["GITHUB_TOKEN"] = creds["github_token"]

        # API Gateway 認証トークン
        if creds.get("api_token"):
            os.environ["API_TOKEN"] = creds["api_token"]

        # vault_root をセットアップ（コールドスタート時のみ）
        vault_root.mkdir(parents=True, exist_ok=True)
        sentinel = vault_root / _SETUP_SENTINEL
        if not sentinel.exists():
            cmd = [
                "ob", "sync-setup",
                "--vault", creds["vault_name"],
                "--path", str(vault_root),
            ]
            if creds.get("vault_password"):
                cmd += ["--password", creds["vault_password"]]
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                stderr = result.stderr.decode(errors="replace")
                stdout = result.stdout.decode(errors="replace")
                raise RuntimeError(
                    f"ob sync-setup failed (rc={result.returncode}): stderr={stderr!r} stdout={stdout!r}"
                )
            sentinel.touch()

    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to set up ob credentials: {exc}") from exc


def ob_sync_pull(vault_root: Path) -> None:
    # obsidian-headless の ob sync は双方向同期。/tmp/vault は起動ごとにリセットされるため
    # pull 時点でローカルに未プッシュの変更はなく、実質的に pull 専用として動作する。
    subprocess.run(["ob", "sync", "--path", str(vault_root)], check=True, capture_output=True)


def ob_sync_push(vault_root: Path) -> None:
    subprocess.run(["ob", "sync", "--path", str(vault_root)], check=True, capture_output=True)


def write_vault_file(vault_root: Path, relative_path: str, content: str) -> None:
    target = vault_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def read_vault_file(vault_root: Path, relative_path: str) -> str:
    return (vault_root / relative_path).read_text(encoding="utf-8")

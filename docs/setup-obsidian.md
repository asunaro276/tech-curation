# Obsidian headless & Secrets Manager setup

## 1.3 obsidian-headless セットアップ

```bash
npm install -g obsidian-headless
ob login          # ブラウザが開くのでObsidianアカウントでログイン
ob sync pull      # vaultが取得できることを確認
```

Lambdaコンテナ内では Dockerfile で自動インストールされる（4.1参照）。
Lambda実行時のクレデンシャルはSecrets Manager経由で注入する（1.4参照）。

## 1.4 AWS Secrets Manager 登録

ob loginで生成されたクレデンシャルファイル（通常 `~/.config/obsidian-headless/credentials.json`）の内容を登録する。

```bash
aws secretsmanager create-secret \
  --name "tech-curation/ob-credentials" \
  --secret-string "$(cat ~/.config/obsidian-headless/credentials.json)"
```

Lambda実行ロールにはこのシークレットの`secretsmanager:GetSecretValue`権限が必要（4.6参照）。

# Obsidian headless & Parameter Store setup

## 1.3 obsidian-headless セットアップ

```bash
npm install -g obsidian-headless
ob login          # ブラウザが開くのでObsidianアカウントでログイン
ob sync pull      # vaultが取得できることを確認
```

Lambdaコンテナ内では Dockerfile で自動インストールされる（4.1参照）。
Lambda実行時のクレデンシャルはParameter Store経由で注入する（1.4参照）。

## 1.4 AWS Systems Manager Parameter Store 登録

ob loginで生成されたクレデンシャルファイル（通常 `~/.config/obsidian-headless/credentials.json`）の内容を登録する。

```bash
aws ssm put-parameter \
  --name "/tech-curation/ob-credentials" \
  --type SecureString \
  --value "$(cat ~/.config/obsidian-headless/credentials.json)" \
  --overwrite
```

Lambda実行ロールにはこのパラメータの`ssm:GetParameter`権限（および復号のための`kms:Decrypt`権限）が必要（4.6参照）。

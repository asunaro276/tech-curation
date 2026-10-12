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

ob login で生成された `auth_token` と vault 名、各 API キーを1つの JSON にまとめて `/tech-curation/ob-credentials` に登録する。
JSON の形式と登録コマンドは [aws-setup.md の手順 3](aws-setup.md#3-ob-login-クレデンシャルを-parameter-store-に登録) を参照。

Lambda実行ロールにはこのパラメータの`ssm:GetParameter`権限（および復号のための`kms:Decrypt`権限）が必要（4.6参照）。

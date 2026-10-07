# AWS Infrastructure Setup

インフラは Terraform で管理し、Lambda のコードデプロイは lambroll v1 で行います。

## 前提条件

- Terraform >= 1.0
- AWS CLI（認証済み）
- Docker
- lambroll v1（`brew install fujiwara/tap/lambroll`）

## 初回デプロイ手順

### 1. Terraform 初期化

```bash
make init
```

S3バックエンド（tfstate-nakano）への接続と AWS provider のインストールを行います。

### 2. インフラ作成

```bash
make apply
```

以下のリソースが作成されます：
- ECR リポジトリ（tech-curation）
- IAM ロール（lambda-role / scheduler-role）
- Parameter Store パラメータ（/tech-curation/ob-credentials, SecureString）
- API Gateway v2（POST /improve エンドポイント）
- EventBridge Scheduler（毎日 07:00 JST → collect Lambda）
- Lambda x2（tech-curation-collect / tech-curation-improve）

### 3. ob login クレデンシャルを Parameter Store に登録

`terraform apply` 完了後、ob login クレデンシャルを手動で投入します（Terraform 側は
`lifecycle.ignore_changes = [value]` によりプレースホルダー値のまま管理対象外にしています）。

```bash
# ob loginを実行してクレデンシャルを生成（初回のみ）
ob login

# Parameter Storeに登録
aws ssm put-parameter \
  --name /tech-curation/ob-credentials \
  --type SecureString \
  --value "$(cat ~/.config/obsidian-headless/credentials.json)" \
  --overwrite
```

### 3.5. LLM / 判定モデルの API キー

collect Lambda は次の環境変数を必要とします（improve Lambda は `DEEPSEEK_API_KEY` のみ）。

| 環境変数 | 用途 |
|---------|------|
| `DEEPSEEK_API_KEY` | 要約・コンテンツ種別判定・レビュー（DeepSeek） |
| `TYPESAFE_API_KEY` | 関連度・トピック判定と記事選定（TypeSafe AI の Jev） |

`TYPESAFE_API_KEY` は `DEEPSEEK_API_KEY` と同じ方法で collect Lambda に設定してください。
未設定の場合も収集は止まりませんが、Jev の判定がすべて失敗扱いになり、全記事の関連度・価値が中立値 0.5 として選定されます（ログに `[jev] ERR(...)` が出ます）。

### 4. コンテナイメージのビルドとデプロイ

```bash
make deploy
```

以下を順番に実行します：
1. `docker build` でイメージをビルド
2. ECR へプッシュ
3. `lambroll deploy --skip-configuration` で collect/improve Lambda を更新

## 通常のデプロイフロー

| 操作 | コマンド |
|------|---------|
| コードを変更してデプロイ | `make deploy` |
| インフラ設定を変更 | `make apply` |
| 差分確認 | `cd terraform && terraform plan` |

## Terraform リソース構成

```
terraform/
  main.tf        # provider + S3 backend
  variables.tf   # aws_region
  outputs.tf     # api_gateway_url, ecr_repository_url
  ecr.tf         # aws_ecr_repository
  iam.tf         # lambda-role + scheduler-role
  secrets.tf     # aws_ssm_parameter
  lambda.tf      # Lambda x2（ignore_changes=[image_uri]）
  api_gw.tf      # HTTP API + integration + route + stage + permission
  scheduler.tf   # aws_scheduler_schedule（daily at 22:00 UTC）
```

## lambroll 設定

```
lambroll/
  collect/function.json   # FunctionName + Code.ImageUri（tfstate参照）
  improve/function.json   # 同上
```

`function.json` は `{{ tfstate \`aws_ecr_repository.this.repository_url\` }}:latest` で
S3上の tfstate から ECR URL を直接参照します。

## Outputs

```bash
cd terraform
terraform output api_gateway_url       # API Gateway エンドポイント
terraform output ecr_repository_url    # ECR リポジトリ URL
```

## Context

langgraph-obsidian-info-agentのAWSインフラは `docs/aws-setup.md` に手動CLIコマンドとして記述されているのみで、IaCが存在しない。2つのLambda（collect/improve）・API Gateway・EventBridge Scheduler・Secrets Manager・ECR・IAMロールを一貫して管理できる体制を整える。

既存実装の制約：
- Lambdaはコンテナイメージ（同一ECRリポジトリ、別ハンドラー）
- collect LambdaはAPI Gateway URLを環境変数として必要とする（Terraformで解決可能）
- Secrets Manager の値（ob loginクレデンシャル）はTerraform管理外とする

## Goals / Non-Goals

**Goals:**
- 全AWSリソースをTerraform HCLで宣言的に定義する
- Lambdaのコードデプロイはlambroll v1 `--skip-configuration` で行う（configはTerraform管理）
- S3バックエンド（tfstate-nakano）でstateを管理する
- Makefileで `make apply`・`make deploy` の2コマンドに集約する

**Non-Goals:**
- CI/CD（GitHub Actions等）は対象外
- 複数環境（dev/prod）の分離は対象外（個人プロジェクト）
- CloudWatch Alarms・モニタリングは対象外
- Secrets Manager の値の自動投入は対象外

## Decisions

### Terraform と lambroll の責任分担

**Lambda configはTerraform、image_uriはlambroll** に分ける。

具体的には：
- Terraform：`aws_lambda_function` リソースで timeout/memory/role/environment を管理。`lifecycle { ignore_changes = [image_uri] }` で lambroll が更新する image_uri を保護する
- lambroll：`lambroll deploy --skip-configuration` でコンテナイメージの更新のみ行う（function configはスキップ）

**理由：** collect Lambda の `API_GATEWAY_URL` は `aws_apigatewayv2_api.this.api_endpoint` から Terraform 内で解決できる。lambroll の function.json に環境変数を書くと Terraform との二重管理になるため、環境変数は Terraform 側に集約する。

**不採用案：** lambroll の function.json に全設定を書き Terraform は `data` ソースで参照する案 → 初回デプロイ順序の制約が生まれ、「Terraform 一発で完結」ができなくなるため却下。

### フラット Terraform ファイル構成

モジュール分割はせず、リソース種別ごとに `.tf` ファイルを分ける。

```
terraform/
  main.tf        # provider, backend
  variables.tf
  outputs.tf
  ecr.tf
  iam.tf
  secrets.tf
  lambda.tf
  api_gw.tf
  scheduler.tf
```

**理由：** 個人プロジェクトで環境が1つ。モジュール化のオーバーヘッドに見合うメリットがない。

### API_GATEWAY_URL の循環依存回避

Terraform は `aws_apigatewayv2_api` → `aws_apigatewayv2_stage` → collect Lambda 環境変数 の順で解決するため、CLIコマンドベースで問題だった循環依存（API GW URL が不明なまま Lambda を作る）が発生しない。

```hcl
environment {
  variables = {
    API_GATEWAY_URL = "${aws_apigatewayv2_api.this.api_endpoint}/${aws_apigatewayv2_stage.prod.name}"
  }
}
```

### Secrets Manager の値管理

`aws_secretsmanager_secret` リソースはTerraformで作成するが、`secret_string` は設定しない。初回 `terraform apply` 後に手動で `aws secretsmanager put-secret-value` を実行する。

**理由：** ob login クレデンシャルをTerraform stateに載せるとS3バケットに平文保存されるリスクがある。

### lambroll function.json の最小化と tfstate 連携

lambroll の `function.json` には `FunctionName` と `Code.ImageUri` のみを記載し、`--skip-configuration` フラグで function config 更新をスキップする。

lambroll v1 には `--tfstate` オプションがあり、function.json 内で `{{ tfstate \`resource.attribute\` }}` テンプレート関数を使って Terraform state から値を直接参照できる。ECR URL を Makefile で注入する代わりに、tfstate から取得する。

```json
{
  "FunctionName": "tech-curation-collect",
  "PackageType": "Image",
  "Code": {
    "ImageUri": "{{ tfstate `aws_ecr_repository.this.repository_url` }}:latest"
  }
}
```

デプロイコマンド：
```bash
lambroll deploy \
  --skip-configuration \
  --tfstate s3://tfstate-nakano/tech-curation/terraform.tfstate \
  --conf lambroll/collect/function.json
```

**理由：** Makefile 内で `terraform output` を呼び出して環境変数に注入する方法より、function.json が自己完結していて見通しが良い。ECR URL のハードコードも不要。

### EventBridge Scheduler

`aws_cloudwatch_event_rule`（旧API）ではなく `aws_scheduler_schedule`（EventBridge Scheduler、新API）を使用する。

**理由：** `aws-setup.md` が既に `aws scheduler create-schedule` を使っており、Terraform の `aws_scheduler_schedule` リソースが対応している。フレキシブルタイムウィンドウ等の新機能も利用可能。

## Risks / Trade-offs

- **初回デプロイ時の image_uri 問題：** `terraform apply` 時点で ECR に有効なイメージが存在しないため Lambda 作成が失敗する可能性がある → ECR リポジトリ作成後、`make build` でダミーイメージをプッシュしてから `terraform apply` を再実行、または `aws_ecr_repository` だけ先に apply する手順をドキュメント化する
- **`ignore_changes = [image_uri]` の落とし穴：** `terraform apply` で image_uri が変化しても無視されるため、意図しないロールバックを防げる反面、Terraform 管理から外れた image_uri は `terraform state` で確認が必要
- **初回 `make deploy` 時の tfstate 参照タイミング：** `terraform apply` が完了してから `make deploy` を実行しないと tfstate に ECR URL が存在しない → 初回は `make apply` → `make deploy` の順序を Makefile の README またはコメントで明記する

## Open Questions

- EventBridge Scheduler の IAM ロール（scheduler.amazonaws.com trust）が ap-northeast-1 で有効か（一部リージョンで未対応の場合 `aws_cloudwatch_event_rule` にフォールバック）

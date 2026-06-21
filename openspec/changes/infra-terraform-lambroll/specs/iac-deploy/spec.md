## ADDED Requirements

### Requirement: Terraform manages all AWS infrastructure
全AWSリソース（ECR・IAM・Secrets Manager・API Gateway v2・EventBridge Scheduler・Lambda x2）はTerraform HCLで定義されなければならない（SHALL）。S3バックエンド（バケット: tfstate-nakano、リージョン: ap-northeast-1）でstateを管理する。

#### Scenario: terraform apply creates all resources
- **WHEN** `terraform apply` を初めて実行する
- **THEN** ECR リポジトリ・IAM ロール x2・Secrets Manager シークレット・API Gateway v2・EventBridge Scheduler・Lambda x2 が作成される

#### Scenario: terraform plan shows no changes after apply
- **WHEN** `terraform apply` 実行後に再度 `terraform plan` を実行する
- **THEN** "No changes" と表示され、インフラが宣言通りであることが確認できる

### Requirement: Lambda image_uri は ignore_changes で保護される
`aws_lambda_function` リソースの `image_uri` は `lifecycle { ignore_changes = [image_uri] }` で保護されなければならない（SHALL）。これにより lambroll によるイメージ更新が次回の `terraform apply` で上書きされない。

#### Scenario: terraform apply does not revert lambroll-deployed image
- **WHEN** lambroll でイメージを更新した後に `terraform apply` を実行する
- **THEN** `image_uri` は変更されず、lambroll がデプロイしたイメージが維持される

### Requirement: API Gateway URL が collect Lambda に自動注入される
collect Lambda の環境変数 `API_GATEWAY_URL` は、Terraform 内で `aws_apigatewayv2_api.this.api_endpoint` と `aws_apigatewayv2_stage.prod.name` から構築され自動的に設定されなければならない（SHALL）。

#### Scenario: collect Lambda has correct API Gateway URL
- **WHEN** `terraform apply` が完了する
- **THEN** tech-curation-collect Lambda の環境変数 `API_GATEWAY_URL` に `https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/prod` が設定されている

### Requirement: Secrets Manager シークレットの値は Terraform 管理外
`aws_secretsmanager_secret` リソースは Terraform で作成されるが、`secret_string`（ob login クレデンシャル）は Terraform で管理してはならない（SHALL NOT）。値は `terraform apply` 後に手動で `aws secretsmanager put-secret-value` で投入する。

#### Scenario: secret resource exists but has no value after terraform apply
- **WHEN** `terraform apply` が完了する
- **THEN** `tech-curation/ob-credentials` シークレットが存在するが、値は空または未設定である

#### Scenario: secret value is set manually post-deploy
- **WHEN** `aws secretsmanager put-secret-value --secret-id tech-curation/ob-credentials --secret-string '...'` を実行する
- **THEN** Lambda が Secrets Manager からクレデンシャルを取得できるようになる

### Requirement: lambroll は --skip-function でイメージのみ更新する
`lambroll deploy` は `--skip-function`（または同等）フラグ付きで実行され、function configuration を更新せずにコンテナイメージのみを更新しなければならない（SHALL）。

#### Scenario: lambroll deploy updates only image_uri
- **WHEN** `lambroll deploy --skip-function --conf lambroll/collect/function.json` を実行する
- **THEN** Lambda の image_uri が新しいECRイメージに更新され、timeout/memory/environment は変更されない

### Requirement: Makefile で init / apply / build / deploy を提供する
`Makefile` は `init`・`apply`・`build`・`deploy` の4ターゲットを持たなければならない（SHALL）。`deploy` ターゲットは `build`（docker build + ECR push）と lambroll デプロイを順番に実行する。ECR URL は `terraform output` から動的に取得する。

#### Scenario: make deploy builds and deploys both Lambdas
- **WHEN** `make deploy` を実行する
- **THEN** Docker イメージがビルドされ ECR にプッシュされた後、collect と improve 両 Lambda が新しいイメージに更新される

#### Scenario: make apply only updates infrastructure
- **WHEN** `make apply` を実行する
- **THEN** `terraform apply` のみが実行され、Docker ビルドや lambroll は実行されない

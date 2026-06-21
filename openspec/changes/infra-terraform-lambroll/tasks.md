## 1. Terraform 基盤セットアップ

- [x] 1.1 `terraform/main.tf` を作成（provider aws ~>5.0、S3バックエンド tfstate-nakano/tech-curation/terraform.tfstate）
- [x] 1.2 `terraform/variables.tf` を作成（aws_region = ap-northeast-1）
- [x] 1.3 `terraform init` を実行してバックエンド接続を確認する

## 2. ECR・IAM・Secrets Manager

- [x] 2.1 `terraform/ecr.tf` を作成（aws_ecr_repository: tech-curation）
- [x] 2.2 `terraform/iam.tf` を作成（lambda-role: BasicExecution + SecretsManager読み取り）
- [x] 2.3 `terraform/iam.tf` に scheduler-role を追加（scheduler.amazonaws.com trust + Lambda invoke権限）
- [x] 2.4 `terraform/secrets.tf` を作成（aws_secretsmanager_secret: tech-curation/ob-credentials、値なし）

## 3. Lambda 定義

- [x] 3.1 `terraform/lambda.tf` に tech-curation-collect を定義（PackageType=Image、timeout=900、memory=1024、ignore_changes=[image_uri]）
- [x] 3.2 tech-curation-collect の environment に VAULT_ROOT・OB_CREDENTIALS_SECRET・API_GATEWAY_URL（api_gw output参照）を設定
- [x] 3.3 `terraform/lambda.tf` に tech-curation-improve を定義（同スペック、別ハンドラー、API_GATEWAY_URLなし）

## 4. API Gateway v2

- [x] 4.1 `terraform/api_gw.tf` を作成（aws_apigatewayv2_api: HTTP API）
- [x] 4.2 aws_apigatewayv2_integration を追加（AWS_PROXY、improve Lambda、payload_format_version=2.0）
- [x] 4.3 aws_apigatewayv2_route を追加（POST /improve）
- [x] 4.4 aws_apigatewayv2_stage を追加（name=prod、auto_deploy=true）
- [x] 4.5 aws_lambda_permission を追加（API Gatewayがimproveを呼び出せるよう許可）

## 5. EventBridge Scheduler

- [x] 5.1 `terraform/scheduler.tf` を作成（aws_scheduler_schedule: cron(0 22 * * ? *)、collect Lambda をターゲット）

## 6. Outputs

- [x] 6.1 `terraform/outputs.tf` を作成（api_gateway_url、ecr_repository_url を出力）

## 7. lambroll 設定

- [x] 7.1 `lambroll/collect/function.json` を作成（FunctionName・PackageType・Code.ImageUri のみ。ImageUri は `{{ tfstate \`aws_ecr_repository.this.repository_url\` }}:latest` で tfstate 参照）
- [x] 7.2 `lambroll/improve/function.json` を作成（同上）

## 8. Makefile

- [x] 8.1 `Makefile` を作成（init・apply・build・deploy の4ターゲット）
- [x] 8.2 `build` ターゲット: ECR ログイン → docker build → docker push（ECR URL は `aws ecr describe-repositories` または terraform output から取得）
- [x] 8.3 `deploy` ターゲット: build → `lambroll deploy --skip-configuration --tfstate s3://tfstate-nakano/tech-curation/terraform.tfstate` x2（collect + improve）

## 9. 動作確認

- [ ] 9.1 `make apply` を実行し全リソースが作成されることを確認（ECR・IAM・APIGW・Scheduler・Lambda x2）
- [ ] 9.2 Secrets Manager に ob login クレデンシャルを手動投入する
- [ ] 9.3 `make deploy` を実行しコンテナイメージがビルド・プッシュされ Lambda が更新されることを確認
- [ ] 9.4 `terraform plan` で "No changes" になることを確認（ignore_changes が機能していること）
- [x] 9.5 `docs/aws-setup.md` を Terraform ベースの手順に更新する

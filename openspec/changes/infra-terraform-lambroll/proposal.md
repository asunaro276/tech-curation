## Why

langgraph-obsidian-info-agentの実装は完了しているが、AWSリソースがコードとして定義されておらず、手動CLIコマンドのドキュメントしか存在しない。TerraformとlambrollでIaCを整備し、再現性のあるデプロイフローを確立する。

## What Changes

- `terraform/` ディレクトリを新規作成し、全AWSリソースをHCLで定義する（ECR・IAM・Secrets Manager・API Gateway v2・EventBridge Scheduler・Lambda x2）
- `lambroll/` ディレクトリを新規作成し、各Lambda関数の `function.json` を配置する
- `Makefile` を追加し、`init` / `apply` / `build` / `deploy` のターゲットを定義する
- 既存の `docs/aws-setup.md` を Terraform ベースの手順に置き換える

## Capabilities

### New Capabilities

- `iac-deploy`: TerraformとlambrollによるAWSインフラのコード化・デプロイ自動化

### Modified Capabilities

## Impact

- **新規ファイル**: `terraform/*.tf`, `lambroll/*/function.json`, `Makefile`
- **更新ファイル**: `docs/aws-setup.md`（手動CLIコマンド → Terraform手順に差し替え）
- **外部依存**: Terraform >= 1.0, AWS provider ~> 5.0, lambroll v1, Docker
- **AWSリソース**: ECR, Lambda x2, API Gateway v2, EventBridge Scheduler, IAM roles x2, Secrets Manager
- **Terraform state**: S3バケット `tfstate-nakano`（ap-northeast-1）

## Why

技術情報の収集・整理を手動で行うコストが高く、情報の見逃しや陳腐化が起きやすい。LangGraphを使ってGitHub・RSS・HackerNews・Substackから自動収集し、Obsidianへ出力するとともに、ユーザーのフィードバックを元にエージェント自身が継続改善するシステムを構築する。

## What Changes

- LangGraphベースの情報収集パイプラインを新規構築（GitHub API・RSS・HackerNews・Substackを並列収集）
- 収集結果をMarkdown形式でObsidian vaultに自動出力（obsidian-headless経由）
- ObsidianノートにPer-itemフィードバック欄を埋め込み、Buttonプラグインで送信
- フィードバックを解析してエージェント設定（ソース重み・クエリ生成プロンプト等）を自己更新するメタ改善ループを実装
- 収集はEventBridge + Lambdaで定期実行、改善ループはローカルPCでボタン起動

## Capabilities

### New Capabilities

- `information-collection`: GitHub API・RSS・HackerNews・Substackから並列収集するLangGraphパイプライン
- `obsidian-output`: 収集結果をper-itemフィードバック欄付きMarkdownに整形し、obsidian-headless経由でObsidian Syncへ書き出す機能
- `feedback-capture`: Obsidianノート内のHTMLコメント形式フィードバックをパースし構造化データに変換する機能
- `self-improvement`: フィードバック履歴を分析してagent_config（数値パラメータ優先、必要時プロンプト編集）を自動更新するメタ改善ループ

### Modified Capabilities

## Impact

- **新規依存**: LangGraph, PyGitHub, feedparser（RSS/HackerNews/Substack共用）, obsidian-headless（npm）
- **AWS**: EventBridge（スケジューラー）, Lambda（コンテナイメージ）, Secrets Manager（ob loginクレデンシャル）
- **Obsidian**: Button Plugin, Shell Commands Plugin, Obsidian Sync サブスクリプション
- **設定ファイル**: `vault/agent-config/prompts.md`（Obsidian vault内に配置、LambdaがSyncで参照）

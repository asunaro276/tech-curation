## 1. プロジェクトセットアップ

- [x] 1.1 Pythonプロジェクト構成を作成（pyproject.toml, src/レイアウト）
- [x] 1.2 依存ライブラリを追加（langgraph, PyGitHub, feedparser, boto3, anthropic）
- [x] 1.3 obsidian-headlessをnpmでインストールし`ob login`でセットアップ
- [x] 1.4 AWS Secrets Managerにob loginクレデンシャルを登録
- [x] 1.5 vault/agent-config/prompts.md の初期ファイルを作成（source_weights初期値・初期プロンプト）
- [x] 1.6 vault/agent-config/topics.md の初期ファイルを作成（アクティブトピックのサンプルを記載）

## 2. 情報収集パイプライン（LangGraph）

- [x] 2.1 CollectStateの型定義（TypedDict）を実装
- [x] 2.2 Planノードを実装（ob sync pullでtopics.md・prompts.mdを取得、LLMでトピックごとにクエリ生成）
- [x] 2.3 GitHubノードを実装（PyGitHubでトレンドリポジトリ・リリース取得）
- [x] 2.4 RSSノードを実装（feedparserで複数フィードURL取得 — 汎用RSS・HackerNews RSS・Substack RSSを統一処理）
- [x] 2.5 Merge&Filterノードを実装（URL重複除去・日付フィルタ・LLM関連度スコアリング）
- [x] 2.6 Summarize&Formatノードを実装（LLM要約・コンテンツ種別判定・テンプレート適用）
- [x] 2.7 並列フェッチのLangGraphエッジを配線（Plan→[GitHub, RSS]並列→Merge）
- [x] 2.8 収集パイプラインの単体テストを作成

## 3. Obsidian出力

- [x] 3.1 Markdownレポート生成関数を実装（YAML frontmatter・per-item構造・`<!-- fb -->`欄・Buttonブロック）
- [x] 3.2 コンテンツ種別ごとのフォーマットテンプレートを3種実装（code/comparison/trend）
- [x] 3.3 ob sync push をsubprocessで呼び出す出力関数を実装

## 4. Lambdaデプロイ

- [x] 4.1 Dockerfile作成（Python + Node.js + obsidian-headless、収集・改善ハンドラーを同梱）
- [x] 4.2 収集Lambda（handler_collect.py）と改善Lambda（handler_improve.py）のエントリーポイントを作成
- [x] 4.3 Lambda関数を2つ作成（タイムアウト15分・メモリ1GB、同一コンテナイメージから別ハンドラー指定）
- [x] 4.4 EventBridgeスケジュールルールを作成（収集Lambdaを定期起動）
- [x] 4.5 API Gatewayに`POST /improve`エンドポイントを作成し改善Lambdaに接続
- [x] 4.6 IAMロールの設定（Secrets Manager読み取り権限）
- [x] 4.7 Lambdaのローカル動作確認（aws-lambda-rie使用）

## 5. フィードバックキャプチャ

- [x] 5.1 HTMLコメントパーサーを実装（正規表現でrelevance/commentを抽出）
- [x] 5.2 未記入コメントのスキップロジックを実装
- [x] 5.3 Obsidian Shell Commands Pluginに`curl -X POST <API_GATEWAY_URL>/improve -d '{"note_path": "{file_path}"}'`を登録
- [x] 5.4 ObsidianのButtonプラグインでフィードバック送信ボタンをレポートテンプレートに追加

## 6. 自己改善パイプライン（LangGraph）

- [x] 6.1 ImproveStateの型定義（TypedDict）を実装
- [x] 6.2 ParseFeedbackノードを実装（ob sync pullで対象ノート取得→HTMLコメントパース→構造化データ）
- [x] 6.3 AnalyzePatternsノードを実装（Script統計計算 + LLM質的解釈）
- [x] 6.4 GenerateChangesノードを実装（LLMによる構造化JSON変更提案）
- [x] 6.5 ApplyChangesノードを実装（JSON読み取り→prompts.md更新→改善履歴追記→status: submitted更新→feedback-history.json追記）
- [x] 6.6 ob sync pushでprompts.md・更新済みノート・feedback-history.jsonをvaultへ書き戻す処理を実装
- [x] 6.7 改善パイプラインの単体テストを作成

## 7. 結合テスト・確認

- [ ] 7.1 収集パイプラインをローカル実行してObsidianにノートが届くことを確認
- [ ] 7.2 フィードバックを記入してボタン押下→API Gateway→改善Lambdaが起動することを確認
- [ ] 7.3 prompts.mdが更新されob sync経由で収集Lambdaの次回実行に反映されることを確認
- [ ] 7.4 Lambda上でのend-to-end実行を確認（収集→Obsidian出力→フィードバック→改善→config更新）

## Context

技術情報を手動で収集・整理するコストを削減するため、LangGraphを用いた自動収集エージェントを構築する。収集結果はObsidian vaultへ出力し、ユーザーがフィードバックを記入してボタンを押すとエージェントが自己改善するループを回す。

インフラ: AWS Lambda（収集・改善ループ）+ API Gateway（改善トリガー）+ Obsidian Sync（データ橋渡し）

## Goals / Non-Goals

**Goals:**
- GitHub・RSS・HackerNews・SubstackからLangGraphで並列収集
- ObsidianノートへPer-itemフィードバック欄付きMarkdownを自動出力
- フィードバックに基づいてagent_config（ソース重み・プロンプト）を自動更新
- EventBridge + Lambdaで定期実行、API Gateway + Lambdaでフィードバック改善ループを起動

**Non-Goals:**
- Web検索（Tavily等）は使用しない
- マルチユーザー対応
- リアルタイム収集（定期バッチで十分）
- Obsidian以外の出力フォーマット

## Decisions

### LangGraphグラフ構造

収集パイプラインと改善パイプラインを2つの独立したグラフとして実装する。

**収集パイプライン:**
```
Plan → [GitHub, RSS, HackerNews, Substack](並列) → Merge&Filter → Summarize&Format → Write
```

**改善パイプライン:**
```
ParseFeedback → AnalyzePatterns → GenerateChanges → ApplyChanges
```

**理由:** 単一グラフにするとスケジュール実行とユーザートリガー実行の起動経路が複雑になる。2グラフに分けることで各パイプラインを独立してテスト・デプロイできる。

### Script vs LLM の分担

| 処理 | 担当 | 理由 |
|------|------|------|
| ソース選択（weight参照） | Script | 決定論的 |
| クエリ生成 | LLM | トピック理解が必要 |
| HTTP/API取得 | Script | 決定論的 |
| URL重複除去・日付フィルタ | Script | 決定論的 |
| 関連度スコアリング | LLM | 意味的判断が必要 |
| 各アイテム要約 | LLM | 生成が必要 |
| コンテンツ種別判定 | LLM | 解釈が必要 |
| Markdownテンプレート適用 | Script | 決定論的 |
| フィードバックパース | Script | 正規表現で十分 |
| 統計計算（ソース別平均等） | Script | 決定論的 |
| パターン解釈 | LLM | 質的判断が必要 |
| 変更内容決定・出力 | LLM（JSON出力） | 判断が必要 |
| config/promptsファイル更新 | Script | LLM出力を適用するだけ |

**原則:** LLMは必ず構造化JSONで出力し、Scriptがファイル更新に適用する。LLMに直接ファイルを触らせない。

### agent_configの保存場所

`vault/agent-config/prompts.md`（Obsidian vault内）を採用。

**理由:** S3やDynamoDBに比べてObsidian上でユーザーが設定の変化を可視化・手動編集できる。ob sync経由でLambdaと共有できるため、追加インフラが不要。

### 改善の優先順位

数値パラメータ（source_weights, filter_threshold, recency_days等）を優先的に調整し、プロンプト直修正は質的変化が必要な場合のみ行う。

**質的変化の判断基準:**
- 「何を関連とみなすか」の定義が変わった → プロンプト編集
- 「どのくらい重視するか」の度合いが変わった → 数値パラメータ

### フィードバック形式

HTMLコメント方式を採用: `<!-- fb: relevance=4, comment=参考になった -->`

**理由:** Obsidianのレンダリングに影響せず視覚的にクリーンで、正規表現によるパースがシンプル。Callout記法（`> [!note]`）はネスト構造のパースが複雑になるため不採用。

### 収集トリガーと改善トリガーの分離

| | 収集 | 改善 |
|--|------|------|
| トリガー | EventBridge（定期） | API Gateway（HTTPエンドポイント） |
| 実行場所 | Lambda（コンテナ） | Lambda（同一コンテナイメージ・別ハンドラー） |
| 起動方法 | 自動 | Obsidian ButtonプラグインからcurlでPOST |

**理由:** 改善ループのスクリプト実行・LLM呼び出しをクラウドに寄せることで、ローカル環境の依存（Python・AWS CLI等）をゼロにできる。収集・改善ともに同一コンテナイメージを共有できるためインフラの管理コストが低い。ローカルPCでやることはObsidian Buttonからのcurlのみとなる。

### HackerNewsのソース実装

HackerNewsはRSS（`https://news.ycombinator.com/rss`）を使用し、feedparserで他のRSSフィードと同一ノードで処理する。

**理由:** Firebase APIより柔軟性は下がるが、RSS統一でコードがシンプルになり、RSSノードの再利用でメンテナンスコストが下がる。

### トピック管理

収集対象トピックを`vault/agent-config/topics.md`として独立したファイルで管理する。prompts.mdとは分離する。

**理由:** トピックはユーザーが頻繁に追加・削除するデータであり、プロンプト設定とライフサイクルが異なる。分離することでObsidian上でトピック一覧が見やすくなり、自己改善ループによる意図しない上書きを防ぐ。

**topics.mdの構造例:**
```markdown
# 収集トピック

## アクティブ
- Rust async ecosystem
- LLM inference optimization
- WebAssembly tooling

## 停止中
- Kubernetes (一時停止)
```

### Obsidian連携

obsidian-headless（npm）を使い、ob syncコマンドでObsidian Syncと通信する。

- **Lambda（収集・改善共通）:** コンテナイメージにNode.js + obsidian-headlessを含め、ob loginクレデンシャルをSecrets Managerに保存
- **収集Lambda:** ob sync pull → 収集実行 → レポート書き出し → ob sync push
- **改善Lambda:** ob sync pull（フィードバックファイル・topics.md・prompts.mdを取得）→ 改善実行 → ob sync push（更新済みprompts.md）

## Risks / Trade-offs

- **Lambda実行時間:** 複数LLM呼び出し + API取得で3〜5分かかる可能性がある → Lambda timeout 15分以内に収める設計とし、ソース数・アイテム数に上限を設ける
- **ob syncの信頼性:** obsidian-headlessはオープンベータ → 同期失敗時はS3へのフォールバック書き出しを検討
- **プロンプト自動書き換えのドリフト:** LLMがプロンプトを繰り返し書き換えると意図しない方向に収束する可能性 → 改善履歴をprompts.mdに残し、ユーザーがObsidianで直接確認・ロールバックできるようにする
- **Secrets Managerのob loginトークン管理:** トークン期限切れ時にLambdaが失敗する → 失敗をCloudWatch Alarmで検知してユーザーに通知する

## Open Questions

- Lambdaコンテナイメージのサイズ: Python + Node.js + 各種依存ライブラリで肥大化しないか（Lambda Layersへの分割を検討）

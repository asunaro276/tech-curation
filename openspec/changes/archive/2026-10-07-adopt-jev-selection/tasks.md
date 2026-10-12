# Tasks

## 1. Jev クライアント

- [x] 1.1 `pyproject.toml` に `typesafe-sdk` を追加して `uv lock` を更新し、`uv run python -c "import typesafe_sdk"` が通ることを確認する
- [x] 1.2 `src/tech_curation/jev.py` を作成する（クライアント生成、`Score`・`Choice`・`Noul` の組み立て、失敗時の中立値）。SDK をモックした単体テストで、正規化（期待スコア 3.0 / 5段階 → 0.75）と例外時の 0.5 が返ることを確認する
- [ ] 1.3 収集 Lambda の環境変数に `TYPESAFE_API_KEY` を設定する手順を `docs/aws-setup.md` に追記し、記載どおりに設定できることを確認する

## 2. 設定

- [x] 2.1 `AgentConfig` に `relevance_criteria`・`worth_criteria`・`topic_quotas` を追加し、`load_config` で `prompts.md` から読み込む。セクションがない場合は既定値になることを単体テストで確認する
- [x] 2.2 `vault/agent-config/prompts.md` に3セクションを追加する（`topic_quotas` の初期値は現行 `select.py` の本数）。`load_config` で読み込んだ値が期待どおりであることをテストで確認する

## 3. Merge&Filter の判定を置き換える

- [x] 3.1 `_score_relevance` を Jev の `relevance`（Score）と `topic`（Choice）の1回の呼び出しに置き換える。RSS のトピックヒントを優先し、失敗時は正規表現による割り当てと関連度 0.5 に戻ることを `tests/test_collect.py` で確認する
- [x] 3.2 正規化した関連度に `_SOURCE_BOOST` と `filter_threshold` を適用し、閾値未満の記事が除外されることをテストで確認する

## 4. Select を置き換える

- [x] 4.1 `select_node` を「各記事を `worth`（Noul）で判定 → トピック内で降順に並べて上位 K 本」に書き換える。上限本数の厳守・未記載トピックへの既定値・最低1本の保証をテストで確認する
- [x] 4.2 全件で判定が失敗した場合に、全記事 0.5 として本数制御だけで選定が完了することをテストで確認する

## 5. 自己改善ループ

- [x] 5.1 `generate_changes` と `revise_proposal` のシステムプロンプトに、`relevance_criteria`・`worth_criteria`・`topic_quotas.<topic>` を変更可能なキーとして追記する
- [x] 5.2 `update_config` が `prompt_changes` の新セクションと `param_changes` の `topic_quotas.<topic>` を `prompts.md` に書き戻せるようにし、`tests/test_improve.py` で確認する

## 6. 結合確認

- [ ] 6.1 過去のレポートに載った記事 20〜30 本で Jev の関連度・トピック・worth を出し、DeepSeek の判定と並べて大きなずれがないか確認する（ずれがあれば基準の文言を調整する）
- [ ] 6.2 ローカルで収集パイプラインを1回実行し、レポートが生成され、各トピックの本数が `topic_quotas` 以内であることを確認する

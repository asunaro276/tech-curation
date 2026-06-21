# Obsidian Plugin Setup

## 5.3 Shell Commands Plugin

Obsidianの設定 → Shell Commands → 新規コマンド追加:

| 項目 | 値 |
|------|-----|
| Command name | フィードバックを送信 |
| Shell command | `curl -X POST https://YOUR_API_ID.execute-api.ap-northeast-1.amazonaws.com/prod/improve -H "Content-Type: application/json" -d '{"note_path": "{{file_path}}"}'` |

`{{file_path}}` はShell Commands Pluginの変数で、現在開いているファイルのパス（vault相対）に展開される。

## 5.4 Button Plugin

レポートテンプレートの末尾に自動生成されるButtonブロック：

````markdown
```button
name フィードバックを送信
type command
action shell:フィードバックを送信
```
````

`report.py` の `generate_report()` がこのブロックを自動的にレポート末尾に追加する。
`API_GATEWAY_URL` 環境変数がLambdaに設定されている必要がある。

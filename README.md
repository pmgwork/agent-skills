# agent-skills

個人用の AI エージェントスキル集である。学術論文の執筆・校正・引用文作成・保存、文章要約、フロントエンドデザイン、After Effects・Blender 操作、プロッターハードウェア操作に関するワークフローをまとめている。

各スキルは、ディレクトリ内の `SKILL.md` を中心に構成される。必要に応じて `references/`、`scripts/`、`tests/`、`agents/` を備える。

## スキル一覧

| スキル | 用途 |
| --- | --- |
| [After Effects MCP](./skills/aftereffects-mcp/) | `@kumoproductions/mcp-aftereffects` を通じて、開いている After Effects プロジェクトのコンポジション、レイヤー、テキスト、図形、エフェクト、マスク、キーフレーム、フッテージ、レンダーキューを安全に確認・操作する。 |
| [Blender MCP](./skills/blender-mcp/) | Blender MCP を通じて、Blender シーンや `.blend` ファイルを段階的に検査し、最小限の編集、スクリーンショット・レンダーによる検証を行う。 |
| [frontend-design](./skills/frontend-design/) | React、Tailwind CSS v4、coss ui、Gen Interface JP で Web サイトやアプリを作成・改修する。coss が定めないページの組版・掲載内容の方針を扱う。 |
| [ochiai-summary](./skills/ochiai-summary/) | 入力された文章・メモ・表・データを、内容の範囲内で落合フォーマットの6見出しに要約する。 |
| [paper-english-proofreading](./skills/paper-english-proofreading/) | 学術論文の英文校正、または日本語原文からの英訳を行う。投稿先・分野の慣習、LaTeX 形式、指定用語を保持する。 |
| [paper2obsidian](./skills/paper2obsidian/) | Markerで抽出し、書誌データ・DOIによる論文ノートへのリンクとともにスクリプト1本でObsidianへ保存する。書誌データが取れない場合だけエージェントが補う。 |
| [paper-writing-scripts](./skills/paper-writing-scripts/) | 日本語学術論文の論理構造・段落構成・である調・句読点を整える。 |
| [plotter-hardware](./skills/plotter-hardware/) | Plotter Hardware の Flask REST API 経由で、AxiDraw、UUNA TEK、M5StickC イレーサーと各アクチュエータを安全に操作する。 |
| [agy-japanese-fix](./skills/agy-japanese-fix/) | Antigravity CLI（agy）の one-shot 実行で日本語を校正・文体統一する。 |

## 構成

```text
skills/
├── aftereffects-mcp/
│   └── agents/
├── blender-mcp/
│   └── agents/
├── frontend-design/
│   ├── agents/
│   └── references/
├── ochiai-summary/
│   └── agents/
├── paper-english-proofreading/
│   └── agents/
├── paper-writing-scripts/
│   └── agents/
├── paper2obsidian/
│   ├── agents/
│   ├── references/
│   ├── scripts/
│   └── tests/
├── agy-japanese-fix/
│   ├── agents/
│   ├── references/
│   └── scripts/
├── plotter-hardware/
│   ├── agents/
│   ├── references/
│   └── scripts/
```

## 使い方

### スキルの自動同期 (`sync.sh`)

本リポジトリのスキルを `~/.agents/skills`（および各エージェントディレクトリ）に一括シンボリックリンク同期できます。

```bash
# ~/.agents/skills への一括同期（リンク作成・更新・孤立リンクの削除）
./sync.sh

# 変更内容の事前確認（ドライラン）
./sync.sh --dry-run

# 現在のリンク状態を確認
./sync.sh --status

# 特定のプロジェクト（例: ./.agents/skills）に同期
./sync.sh -t ./.agents/skills

```

同期先に同名のファイル・ディレクトリ・別のリンクがある場合は保持し、競合を報告して終了コード1を返す。`-t` 指定時は指定先だけを変更し、エージェント用エイリアスは作成しない。`--install-hook` は未対応。

### スキルの呼び出し

1. 対象スキルの `SKILL.md` を読み込ませる、またはエージェントからスキル名を指定する。
2. 必要に応じて `references/` の資料と `scripts/` の補助ツールを利用する。

各スキルの `SKILL.md` に、前提条件・処理手順・出力形式・安全上の注意を記載している。

## 注意事項

- `aftereffects-mcp` は After Effects と `@kumoproductions/mcp-aftereffects` サーバーが利用可能な環境で使用する。操作前にプロジェクトの状態を確認し、変更後は読み戻しやプレビューで検証する。
- `paper2obsidian` は Marker（`uv tool install marker-pdf`）で下書きを作り、文字化けやスキャンPDFのときだけ OCR（llama.cpp の `llama-server` が必要）に切り替える。`scripts/run.py` が変換から保存後の検査まで行う。抽出の小さな誤りは直さない。書誌データと参考文献のリンクは Crossref の登録データで決める。通常の保存先は `PAPER_SAVE_VAULT_ROOT` を使用する。
- `plotter-hardware` は実機を動かしたり、ソレノイドを作動させたりするため、状態確認と対象操作の明示的な依頼が必要である。
- ハードウェア操作の詳細なエンドポイント、座標範囲、実行条件は各スキルの `references/` と `SKILL.md` を正本とする。

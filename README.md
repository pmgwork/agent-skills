# agent-skills

個人用の AI エージェントスキル集である。学術論文の執筆・校正・引用文作成・保存、文章要約、フロントエンドデザイン、プロッターハードウェア操作に関するワークフローをまとめている。

各スキルは、ディレクトリ内の `SKILL.md` を中心に構成される。必要に応じて `references/`、`scripts/`、`tests/`、`agents/` を備える。

## スキル一覧

| スキル | 用途 |
| --- | --- |
| [frontend-design](./skills/frontend-design/) | 既存の Web サイトやアプリの機能・情報構造を保ったまま、余白・無彩色・1px border・控えめな角丸を基調とした UI に差し替える。Tailwind CSS と shadcn/ui を前提とする。 |
| [ochiai-summary](./skills/ochiai-summary/) | 入力された文章・メモ・表・データを、内容の範囲内で落合フォーマットの6見出しに要約する。 |
| [paper-english-proofreading](./skills/paper-english-proofreading/) | 学術論文の英文校正、または日本語原文からの英訳を行う。投稿先・分野の慣習、LaTeX 形式、指定用語を保持する。 |
| [paper-references-citation](./skills/paper-references-citation/) | 論文の抄録・要約・本文抜粋から、日本語学術論文の関連研究や序論で使える引用文を作成する。 |
| [paper-save](./skills/paper-save/) | 論文 PDF を Docling で抽出し、整形した原文・画像・原本 PDF・BibTeX とともに Obsidian vault へ保存する。 |
| [paper-writing-scripts](./skills/paper-writing-scripts/) | 日本語学術論文の論理構造・段落構成・である調・句読点を整える。 |
| [plotter-hardware](./skills/plotter-hardware/) | Plotter Hardware の Flask REST API 経由で、AxiDraw、B1 イレーサー、B3 ペン、D2 ソレノイドを安全に操作する。 |

## 構成

```text
skills/
├── frontend-design/
├── ochiai-summary/
├── paper-english-proofreading/
├── paper-references-citation/
├── paper-save/
│   ├── agents/
│   ├── references/
│   ├── scripts/
│   └── tests/
├── paper-writing-scripts/
└── plotter-hardware/
    ├── agents/
    ├── references/
    └── scripts/
```

## 使い方

1. 利用するスキルのディレクトリを、使用する AI エージェントのスキル配置先へ追加する。
2. 対象スキルの `SKILL.md` を読み込ませる、またはエージェントからスキル名を指定する。
3. 必要に応じて `references/` の資料と `scripts/` の補助ツールを利用する。

各スキルの `SKILL.md` に、前提条件・処理手順・出力形式・安全上の注意を記載している。

## 注意事項

- `paper-save` は Docling と Obsidian vault を使用する。保存先やメタデータを確認してから実行する。
- `plotter-hardware` は実機を動かしたり、ソレノイドを作動させたりするため、状態確認と対象操作の明示的な依頼が必要である。
- ハードウェア操作の詳細なエンドポイント、座標範囲、実行条件は各スキルの `references/` と `SKILL.md` を正本とする。

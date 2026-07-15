# skills

個人用のスキル集です。学術論文の執筆・校正・要約を中心としたワークフローと、フロントエンドデザインの指針をまとめています。各スキルは `SKILL.md` を中心としたプロンプト・指針として記述してあり、Claude Code をはじめ、対応する各種 AI エージェントやツールから読み込んで利用できます。

## スキル一覧

| スキル | 用途 |
| --- | --- |
| [axicli](./skills/axicli/) | AxiDraw 用 SVG の点検・プレビュー・実機プロット・再開操作を、安全確認付きで行います。 |
| [bothub-hardware](./skills/bothub-hardware/) | BotHub Hardware REST API 経由で AxiDraw と GPIO ソレノイドを安全に操作します。 |
| [paper-save](./skills/paper-save/) | 論文 PDF の構造と読み順をAIで整えた原文・全画像・原本 PDF・BibTeX を Obsidian vault に保存します。 |
| [paper-summary](./skills/paper-summary/) | 論文 PDF から論文情報・Figure 1・日本語要約・BibTeX を抽出し、Obsidian vault に研究ノートとして登録します。 |
| [paper-references-citation](./skills/paper-references-citation/) | 論文の抄録・本文抜粋から、日本語学術論文の関連研究や序論で使える簡潔な引用文を作成します。 |
| [paper-english-proofreading](./skills/paper-english-proofreading/) | 学術論文の英文校正、または日本語原文からの英訳を行います。投稿先・分野の慣習や LaTeX 形式、指定用語を保持します。 |
| [paper-writing-scripts](./skills/paper-writing-scripts/) | 日本語の学術論文を、論理構造・段落構成・である調・句読点の観点から執筆・推敲します。 |
| [frontend-design](./skills/frontend-design/) | 既存の Web サイトや Web アプリの UI を、余白・無彩色・1px border・控えめな角丸を基調としたデザインへ差し替えます。Tailwind CSS と shadcn/ui を前提とします。 |

## 構成

各スキルはそれぞれのディレクトリに `SKILL.md` を持ち、必要に応じて参照資料（`references/`）を備えています。

```
skills/
├── axicli/
├── bothub-hardware/
├── frontend-design/
├── paper-english-proofreading/
├── paper-references-citation/
├── paper-save/
├── paper-summary/
└── paper-writing-scripts/
```

## 使い方

各スキルの `SKILL.md` を、お使いの AI エージェントやツールにスキル・プロンプトとして読み込ませて利用します。詳細は、それぞれの `SKILL.md` をご覧ください。

---
name: paper-summary
description: 論文 PDF から論文情報・Figure 1・日本語要約・BibTeX を抽出し、Obsidian vault に研究ノートとして登録するときに使う。
---

# 学術論文登録システム

論文 PDF から論文情報、Figure 1、日本語要約、BibTeX を抽出し、Obsidian vault に研究ノートとして登録する。

## ワークフロー

ユーザーが論文 PDF を指定またはアップロードしたら、以下を順番に実行する。

1. 論文情報と Figure 1 を抽出する。
2. 落合フォーマットで日本語要約を作成する。
3. Obsidian vault に Markdown、PDF、Figure 1 画像を保存する。
4. 保存結果と主要情報を報告する。

## Step 1: 情報抽出

PDF からの本文抽出、構造化、Figure 1 抽出は Docling だけを使う。Docling 変換は 1 PDF につき 1 回だけ実行し、その出力を本文抽出と Figure 1 判定の両方に使う。変換コマンド、Markdown 出力、OCR の扱いは `references/pdf_parsing.md` に従う。

抽出する基本情報:

- `Title`: 論文の英語タイトル。原文のまま記録する。
- `タイトル`: 英語タイトルを日本語へ翻訳したタイトル。
- `year`: 出版年。西暦の数値。
- `doi`: DOI リンクまたは公開 URL。Docling 出力と PDF 内に明示がない場合は「情報なし」。
- `tags`: `paper/` から始まる Obsidian タグ。既存タグで不足する場合は新しい `paper/{tag}` を追加してよい。
- `authors`: `著者名（所属機関名）` の形式。PDF 内に所属が明示されていない場合は「所属不明」。
- `source`: ジャーナル情報または会議名。
- `bibtex`: コピーできる完全な BibTeX。key は `references/naming.md` の規則に従い、必ず小文字にする。
- `rating`: `★`、`★★`、`★★★` のいずれか。掲載先、新規性、技術難易度、結果の説得力、学術的インパクトで評価する。

既存タグ:

```text
paper/bci, paper/ar, paper/vr, paper/motor, paper/speech,
paper/game, paper/music, paper/emotion, paper/locomotion,
paper/fitts, paper/ssvep, paper/onomatopoeia, paper/ear,
paper/visual, paper/transition, paper/errp, paper/haptics,
paper/benchmark, paper/pseudo-haptics, paper/embodiment,
paper/ui, paper/impedance, paper/gesture
```

Figure 1 の抽出は `references/figure_extraction.md` に従う。抽出できない場合は frontmatter の `figure` と本文冒頭の画像埋め込みを作らない。

## Step 2: 日本語要約

落合フォーマット（6 見出し）で日本語要約を作成する。見出しの構成と順序、文体ルール、関連論文リンク `[[{SanitizedTitle}|{Title}]]` の規則は `references/summary_format.md` に従う。

## Step 3: Obsidian 登録

vault ルートの解決、保存先パス、frontmatter、本文テンプレート、重複回避、保存後検証は `references/registration.md` に従う。タイトル、ファイル、リンク、BibTeX key の命名規則は `references/naming.md` に従う。

特に重要な原則:

- `{SanitizedTitle}` は英語タイトルから一度だけ生成し、Markdown 名、PDF 名、assets フォルダ名、各リンク、Obsidian ノートリンクで同じ値を使う。原題や日本語タイトルをファイル名やリンク先に直接使わない。
- 本文 `.md` は Write で直接書き、PDF と Figure 1 画像は vault ルート配下へコピーする。長い構造化ノートやバイナリ資産を `obsidian create` で流し込まない。CLI は vault パスの解決と、登録後の検証・オープンに限定して使う。
- 同名ノートまたは同名 PDF が存在する場合は、上書きせず `references/naming.md` の重複時ルールに従う。

## Step 4: 完了報告

登録後、以下を報告する。

1. 登録されたノートのタイトル
2. 作成した Obsidian ノートのパス
3. 保存した PDF のパス
4. 保存した Figure 1 画像のパス、または抽出できなかった理由
5. 抽出・登録された主要情報の要約
6. 自動評価した `★` / `★★` / `★★★` の評価理由
7. 追加したタグがある場合は、タグ名と理由

保存後の検証は `references/registration.md` のチェックリストに従う。

## 参照ファイル

- `references/pdf_parsing.md`: Docling による PDF 変換、Markdown 出力、OCR、構造化抽出の手順。
- `references/figure_extraction.md`: Figure 1 抽出の詳細手順。
- `references/summary_format.md`: 要約フォーマット、文体、次に読むべき論文リンク規則。
- `references/naming.md`: タイトル、ファイル、リンク、BibTeX key の命名規則。
- `references/registration.md`: vault 解決、保存先パス、frontmatter、本文テンプレート、保存・検証の詳細。

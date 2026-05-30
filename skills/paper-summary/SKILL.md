---
name: paper-summary
description: PDF から論文情報を抽出し、日本語要約を作成して、Obsidian vault に研究ノートとして登録する。
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

PDF からの本文抽出、構造化、Figure 1 抽出は Docling だけを使う。Docling 変換は 1 PDF につき 1 回だけ実行し、その出力を本文抽出と Figure 1 判定の両方に使う。具体的な変換方法、Markdown 出力、画像出力は `references/pdf_parsing.md` と `references/figure_extraction.md` に従う。

Docling は付属の CLI を `uvx` 経由で実行する。基本コマンドは次のとおりで、入力 PDF と出力先は絶対パスで指定する。通常の論文 PDF では OCR を使わず、スキャン PDF の場合だけユーザーに確認して `--ocr` を付ける。詳細は `references/pdf_parsing.md` に従う。

```bash
uvx --from "docling-slim[standard]" docling "<input.pdf>" \
  --to md --image-export-mode referenced --device cpu --no-ocr \
  --output "<work/docling>"
```

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

Figure 1 の抽出は、Docling が出力した Markdown 上の Figure 1 caption とその近傍の画像参照（`<PDF名>_artifacts/` 内の PNG）を読み取って同定する。詳細は `references/figure_extraction.md` に従う。抽出できた場合は `papers/assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png` として保存し、frontmatter の `figure` と本文冒頭に入れる。抽出できない場合は `figure` と本文冒頭の画像埋め込みを作らない。

## Step 2: 日本語要約

落合フォーマット（6 見出し）で日本語要約を作成する。見出しの構成と順序、各見出しで書く内容、文体ルール（である調、句点 `．`・読点 `，`、文章形式、大学院生向け）、および関連論文リンク `[[{SanitizedTitle}|{Title}]]` の規則と例は `references/summary_format.md` に従う。

## Step 3: Obsidian 登録

保存先 vault は、特に指定がなければ現在アクティブな（最後にフォーカスした）vault とする。保存先フォルダはユーザー指定がない限り `papers`。アクティブ vault の絶対パスは Obsidian CLI で取得し、`<VAULT_ROOT>` として使う。

```bash
obsidian vault info=path
```

別の vault に保存したい指定がある場合は、`obsidian vaults verbose`（`名前<TAB>絶対パス`）の一覧から、その vault 名の行のパスを使う。

本文 `.md` は Write でファイルを直接書き、PDF と Figure 1 画像は解決した vault ルート配下へコピーする。長い構造化ノートやバイナリ資産を `obsidian create` で流し込まない。CLI は vault パスの解決と、登録後の検証・オープンに限定して使う。

```text
<VAULT_ROOT>/papers/{SanitizedTitle}.md
<VAULT_ROOT>/papers/assets/{SanitizedTitle}/{SanitizedTitle}.pdf
<VAULT_ROOT>/papers/assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png
```

登録方法、vault ルートの解決、frontmatter、本文テンプレート、重複回避、保存後検証は `references/registration.md` に従う。タイトル、ファイル、リンク、BibTeX key の命名規則は `references/naming.md` に従う。

重要な必須事項:

- `{SanitizedTitle}` は英語タイトルから一度だけ生成し、Markdown 名、PDF 名、assets フォルダ名、PDF リンク、Figure リンク、Obsidian ノートリンクで同じ値を使う。
- 原題や日本語タイトルをファイル名、フォルダ名、リンク先に直接使わない。
- PDF は `papers/assets/{SanitizedTitle}/{SanitizedTitle}.pdf` にコピーする。
- Figure 1 を抽出できた場合は `papers/assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png` に保存する。
- Markdown には PDF 埋め込み `![[assets/{SanitizedTitle}/{SanitizedTitle}.pdf]]` を入れる。
- Figure 1 を抽出できた場合は frontmatter に `figure: "assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png"` を入れ、本文の最上部にも `![[assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png]]` を入れる。
- 同名ノートまたは同名 PDF が存在する場合は、上書きせず同じ識別子を Markdown、PDF、PDF 用フォルダ、Figure 1 画像に付与する。

## Step 4: 完了報告

登録後、以下を報告する。

1. 登録されたノートのタイトル
2. 作成した Obsidian ノートのパス
3. 保存した PDF のパス
4. 保存した Figure 1 画像のパス、または抽出できなかった理由
5. 抽出・登録された主要情報の要約
6. 自動評価した `★` / `★★` / `★★★` の評価理由
7. 追加したタグがある場合は、タグ名と理由

## 検証

保存後は Markdown を読み戻し、以下を確認する。

- 文字化け、欠落、frontmatter の崩れがない。
- BibTeX が欠落していない。
- BibTeX key がすべて小文字で、`references/naming.md` の規則に従っている。
- Markdown ファイル名、PDF ファイル名、PDF 用フォルダ名、PDF 埋め込みリンク、Figure 1 リンクの `{SanitizedTitle}` が一致している。
- PDF が存在し、サイズが 0 byte ではない。
- Figure 1 を保存した場合、PNG が存在し、サイズが 0 byte ではなく、frontmatter と本文冒頭のリンクに一致している。

## 参照ファイル

- `references/figure_extraction.md`: Figure 1 抽出の詳細手順。
- `references/pdf_parsing.md`: Docling による PDF 変換、Markdown 出力、OCR、構造化抽出の手順。
- `references/summary_format.md`: 要約フォーマット、文体、次に読むべき論文リンク規則。
- `references/naming.md`: タイトル、ファイル、リンク、BibTeX key の命名規則。
- `references/registration.md`: frontmatter、本文テンプレート、保存・検証の詳細。

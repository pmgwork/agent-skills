---
name: paper-save
description: 論文PDFをDoclingで抽出し、原文を軽く整形して全画像、原本PDF、BibTeXとともにObsidian vaultへ新規保存する。論文を要約・翻訳せずアーカイブする依頼、論文PDFをObsidianへ登録する依頼で使う。
---

# Paper Save

論文PDFを、要約や翻訳をせずObsidianへ保存する。Docling出力を基本とし、明らかな抽出崩れだけを原本PDFで直す。評価、タグ、関連論文推薦、参考文献一覧は生成しない。

以降の `scripts/...` コマンドは、この `SKILL.md` があるスキルフォルダをカレントディレクトリとして実行する。

## ワークフロー

1. 保存先、メタデータ、命名、重複、OCRモードを確定する。
2. Doclingを1回実行し、画像参照を後処理する。
3. 本文を軽く整形し、Figure 1をサムネイルに指定して最終ノートを組み立てる。
4. 最小検証を行い、vaultへ保存する。

## 1. 事前確認

保存先とノート形式は `references/registration.md`、正式メタデータとBibTeXは `references/metadata.md`、ファイル名とcitekeyは `references/naming.md` に従う。

メタデータは通常、高速モードで取得する。まずPDF内の情報を使い、ネットワーク照合は不足または曖昧な項目がある場合だけ行う。ユーザーが公式情報の厳密な照合を明示した場合のみ、完全な公式照合フローを使う。

vaultルートを解決し、`papers` とvault外の作業フォルダを用意する。
`PAPER_SAVE_VAULT_ROOT` が設定されていれば、そのパスを既定値として使う。
ユーザーがvaultを指定済みなら、その保存先を再確認せず、環境変数より優先する。
環境変数もユーザー指定もない場合は、保存処理を始める前にvaultルートをユーザーへ尋ねる。
vaultルートの解決にObsidian CLIは使用しない。

```bash
mkdir -p "<VAULT_ROOT>/papers"
paper_save_work="$(mktemp -d)"
```

以降の `<work>` は、この作業フォルダの絶対パスへ置き換える。

正式タイトルから `{SanitizedTitle}` とcitekeyを確定したら、処理前に重複を確認する。

```bash
python3 scripts/save_paper.py \
  --check-only \
  --papers-dir "<VAULT_ROOT>/papers" \
  --sanitized-title "{SanitizedTitle}"
```

衝突時は上書きや自動改名をせず中止する。

OCRが必要と判定した場合は、Docling実行前にチャットで明示してから、そのままOCR変換を続行する。

## 2. Docling変換

`references/pdf_parsing.md` に従い、OCRモードを判定してDoclingを1回実行する。
`pdftotext` がない、または判定に失敗した場合は、確認せず `no-ocr` を使う。

```bash
python3 scripts/detect_pdf_text.py "<input.pdf>"
```

変換後、全PNGを採番して画像参照をObsidian形式へ変換する。

```bash
python3 scripts/postprocess_docling.py \
  --markdown "<work/docling>/<PDF名>.md" \
  --artifacts-dir "<work/docling>/<PDF名>_artifacts" \
  --output-markdown "<work/final/prepared.md>" \
  --output-artifacts-dir "<work/final/artifacts>" \
  --asset-link-prefix "assets/{SanitizedTitle}/artifacts"
```

## 3. 本文整形

`prepared.md` を `references/content_formatting.md` に従って整形する。Doclingの文章、見出し、読み順を基本採用し、多段組み、数式、Figureとcaptionなどに明らかな崩れがある箇所だけ原本PDFと照合する。全ページ確認や見出しmap作成は行わない。

Docling出力と確定済みメタデータに矛盾が見つかった場合は保存しない。`references/metadata.md` に従って値を確定し直し、`{SanitizedTitle}` とcitekeyを再生成して `--check-only` を再実行する。

参考文献一覧は見出しと内容を除外する。本文中の引用記号は残し、参考文献より後に同階層以上のAppendix等があれば、そこから本文の保存を再開する。

Figure 1 / Fig. 1 / 図1のcaptionに対応する最初の画像を特定し、`figure: "assets/{SanitizedTitle}/artifacts/image_NNN.png"` としてfrontmatterへ追加する。出版社ロゴなど単に最初に抽出された画像を使わない。Figure 1を確実に特定できない場合だけ `figure` を省略する。

frontmatter、整形済み本文、PDF埋め込み、BibTeXを `<work/final/note.md>` にまとめる。

## 4. 保存

`scripts/save_paper.py` でMarkdown整形、最小検証、保存をまとめて行う。

```bash
python3 scripts/save_paper.py \
  --markdown "<work/final/note.md>" \
  --paper-pdf "<input.pdf>" \
  --artifacts-dir "<work/final/artifacts>" \
  --papers-dir "<VAULT_ROOT>/papers" \
  --sanitized-title "{SanitizedTitle}"
```

このスクリプトは重複、入力と保存結果の非0 byte、PNG、PDF埋め込み、画像埋め込み、サムネイル参照先を確認する。既存ノートは編集しない。

## 完了報告

次を簡潔に報告する。

1. 正式英語タイトル
2. ノートとPDFの保存先
3. 画像数、artifactsフォルダ、サムネイル画像
4. BibTeX key
5. 公式情報で補完できなかったメタデータ
6. OCRモードと保存結果

## 参照ファイル

- `references/pdf_parsing.md`: DoclingとOCRの規則。
- `references/content_formatting.md`: 軽量な本文整形と参考文献除外の規則。
- `references/metadata.md`: 公式メタデータとBibTeX。
- `references/naming.md`: ファイル、画像、リンク、citekeyの命名規則。
- `references/registration.md`: vault構造とノート形式。

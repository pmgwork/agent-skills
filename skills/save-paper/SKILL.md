---
name: save-paper
description: 論文PDFをDoclingで抽出し、原文を整形して全画像、原本PDF、BibTeXとともにObsidian vaultへ新規保存する。論文を要約・翻訳せずアーカイブする依頼、論文PDFをObsidianへ登録する依頼で使う。
---

# Save Paper

論文PDFを、要約や翻訳を行わずにDoclingで構造抽出し、**原本PDF・全画像・メタデータ・BibTeX** とともに Obsidian Vault へ新規保存する。

---

## 前提とVault構造

- **Vaultルート（必須環境変数）**: 環境変数 `PAPER_SAVE_VAULT_ROOT` を使用する。
  - **未設定の場合**: 処理を中断し、ユーザーへ設定コマンドを案内して設定完了を待つ（「`PAPER_SAVE_VAULT_ROOT` が設定されていません。以下のコマンドを実行して設定し、設定が完了したら教えてください」と案内する。パスの直接入力で処理を続行しない）。
    ```bash
    echo "export PAPER_SAVE_VAULT_ROOT=\"<Obsidian Vaultの絶対パス>\"" >> ~/.zshrc
    source ~/.zshrc
    ```
  ※ **Vaultルートの解決に Obsidian CLI は使用しない。**
- **保存先ディレクトリ構造**:
  ```text
  <VAULT_ROOT>/papers/
  ├── {SanitizedTitle}.md
  └── assets/
      └── {SanitizedTitle}/
          ├── {SanitizedTitle}.pdf
          └── artifacts/
              ├── image_001.png
              └── image_002.png
  ```

---

## ワークフロー

### 1. Docling実行

作業用の一時ディレクトリを用意し、Doclingを実行して Markdown と画像を抽出する。

```bash
work_dir="$(mktemp -d)"

# テキストPDFの場合
docling convert "<input.pdf>" \
  --to md \
  --image-export-mode referenced \
  --device cpu \
  --no-ocr \
  --output "$work_dir"

# スキャンPDF（テキストが含まれない場合）は --ocr を指定
```

### 2. メタデータ確認 & 重複チェック

1. 生成された `$work_dir/<PDF名>.md` の先頭から、正式英語タイトル、出版年、DOI、著者名、掲載先（会議・ジャーナル名）を確認する。
2. 以下の命名規則に従い、`citekey` を作成する（例: `smith2026modular`）。
   - `{第一著者姓}{出版年4桁}{タイトル先頭語（a, an, theを除く）}`
3. 重複チェックを実行する。
   ```bash
   python3 scripts/save_paper.py \
     --title "<Official English Title>" \
     --pdf "<input.pdf>" \
     --markdown "$work_dir/<PDF名>.md" \
     --check-only
   ```
   ※ 既存ノートまたは同名の画像フォルダが存在する場合は、上書きせず処理を中断する。

### 3. ノートの組み立て

Doclingが出力したMarkdownをもとに、以下の構成で `<work_dir>/note.md` を作成する。

```markdown
---
title: "Official English Title"
year: 2026
doi: "https://doi.org/..."
authors:
  - "First Author"
  - "Second Author"
source: "Conference or Journal Name"
citekey: author2026title
figure: "assets/{SanitizedTitle}/artifacts/image_001.png"
---

## Abstract

（Abstractがある場合のみ原文テキスト）

## 1. Introduction

（整形された本文...）

## PDF

![[assets/{SanitizedTitle}/{SanitizedTitle}.pdf]]

## BibTeX

```bibtex
@inproceedings{author2026title,
  author = {First Author and Second Author},
  title = {Official English Title},
  year = {2026},
  doi = {10...}
}
```
```

#### 本文整形のルール
- **除外する項目**: 参考文献一覧（References / Bibliography）、ページヘッダー・フッター、著作権定型文、重複する著者所属・メールアドレス。
- **保持する項目**: 見出し階層、数式、表、謝辞、Appendix。
- **サムネイル（figure）**: Figure 1に対応する画像が特定できた場合のみfrontmatterに設定（特定できなければ省略）。

### 4. Vaultへの保存実行

統合スクリプトを実行し、画像の採番・Obsidianリンク置換・PDFコピー・Vault保存を一括で行う。

```bash
python3 scripts/save_paper.py \
  --title "<Official English Title>" \
  --pdf "<input.pdf>" \
  --markdown "$work_dir/note.md" \
  --docling-artifacts "$work_dir/<PDF名>_artifacts"
```

### 5. 完了報告

保存完了後、以下を簡潔にユーザーに報告する。
- 正式英語タイトル
- 保存先ノート（`.md`）およびPDFのパス
- 抽出・保存した画像枚数
- BibTeX citekey

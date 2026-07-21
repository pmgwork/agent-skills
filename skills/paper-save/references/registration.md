# Obsidian登録

## vaultルート

ユーザー指定がなければ現在アクティブなvaultの `papers` へ保存する。

```bash
obsidian vault info=path
```

別vaultが指定された場合は `obsidian vaults verbose` から対応する絶対パスを解決する。Obsidian CLIが利用できなければ、書き込み前にvaultルートをユーザーへ確認する。

## 保存構造

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

## 重複防止

書き込み前に次を確認する。

- `papers/{SanitizedTitle}.md` が存在しない。
- `papers/assets/{SanitizedTitle}/` が存在しない。
- `papers/assets/{SanitizedTitle}/{SanitizedTitle}.pdf` が存在しない。
- frontmatterの `citekey` が既存の `papers/*.md` に存在しない。

いずれかが衝突した場合は、上書きも自動サフィックス付与もせず中止する。既存ノートや既存assetsフォルダの内容を変更しない。

## ノート形式

````markdown
---
title: "Official English Title"
year: 2026
doi: "https://doi.org/..."
authors:
  - "Author Name"
source: "Conference or Journal"
citekey: author2026title
---
## Abstract

Abstract相当が存在する場合のみ、その原文……

## 原論文の最初の主要章

AIで構造と読み順を整えた原文……

## PDF

![[assets/{SanitizedTitle}/{SanitizedTitle}.pdf]]

## BibTeX

```bibtex
@inproceedings{author2026title,
  ...
}
```
````

frontmatterの文字列は二重引用符で囲み、内部の `"` と `\\` をYAMLとしてエスケープする。`year` が不明な場合は `year: ""`、著者が不明な場合は `authors: []` とする。

本文は `references/content_formatting.md` に従ってAI整形する。Abstractがない論文では `## Abstract` を省略し、原論文の最初の主要章から始める。原文を要約、翻訳、説明追加、言い換えしない。後処理した画像は作業フォルダで個数と名前を確認してから、PDFとともにファイルシステム操作でvaultへコピーする。長いMarkdownやバイナリを `obsidian create` へ渡さない。

vaultへ書き込む前に `scripts/format_final_markdown.py` を実行し、整形後のMarkdownだけを保存する。

## 保存後の検証

作成したMarkdownを読み戻し、次を確認する。

- frontmatterが構文上成立し、必須7項目が存在する。
- H1、論文タイトルの重複、`原文`、`本文` のコンテナ見出しが存在しない。
- Abstract相当がある場合だけ `## Abstract` が存在し、その原文が保持されている。
- 原論文の主要章、`## PDF`、`## BibTeX` が同じH2階層にある。
- 原論文の見出し名、順序、相対階層が保持され、標準的な章名が捏造されていない。
- 多段組みの読み順が復元され、隠しテンプレート文字、著者情報、出版定型文が本文に残っていない。
- 実質的な論文本文、caption、表、数式、本文中の引用、参考文献で挙げられた作品が欠落していない。
- 参考文献一覧が、原文と同じ番号・順序の `1. [[{SanitizedTitle}|{OfficialTitle}]]` 形式だけで構成されている。
- 参考文献リンク数が原文の参考文献項目数と一致し、著者、年、掲載先、ページ、DOIが一覧に残っていない。
- 本文中の引用記号が原文のまま維持され、Referencesの番号と対応している。
- Docling由来のインライン数式がLaTeXへ復元され、`0 . 5`、`𝑝 < =` のような分離文字が残っていない。
- frontmatter直後の最初のATX見出しとの間に空行がなく、それ以外のATX見出しの直前とすべてのATX見出しの直後に空行があり、References最終リンクと `## PDF` の間にも空行がある。
- すべてのFigureが `画像埋め込み → 空行 → 原文caption` の順で配置されている。
- すべてのObsidian画像リンクが実在する非0 byteのPNGを指す。
- Doclingの全PNGが `artifacts/` に保存されている。
- PDF埋め込みが実在する非0 byteのPDFを指す。
- BibTeX keyとfrontmatterの `citekey` が一致し、命名規則に従う。
- BibTeXの数値ページ範囲が `--` で表記され、曲線引用符や範囲用Unicodeダッシュが残っていない。
- Docling作業ディレクトリ、`<PDF名>_artifacts`、元画像名へのリンクが残っていない。
- 日本語要約、翻訳、説明文、rating、tags、Figure 1専用画像が追加されていない。
- 登録前に存在した論文ノートの内容が変更されていない。

Obsidian CLIが使える場合は最後に読み戻しと提示へ利用してよい。

```bash
obsidian read path="papers/{SanitizedTitle}.md"
obsidian open path="papers/{SanitizedTitle}.md"
```

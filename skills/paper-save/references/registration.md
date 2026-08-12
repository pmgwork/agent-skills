# Obsidian登録

## vaultと保存構造

`PAPER_SAVE_VAULT_ROOT` が設定されていれば、そのパスを既定のVaultルートとして使用する。ユーザーがvaultを指定した場合は、そのパスを再確認せず使用し、環境変数より優先する。両方とも未設定の場合は、書き込み前にvaultルートをユーザーへ尋ねる。vaultルートの解決にObsidian CLIは使用しない。

環境変数の設定例:

```bash
export PAPER_SAVE_VAULT_ROOT="/Users/yuto/Documents/Obsidian/MyVault"
```

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

`papers` がなければ作成する。処理ごとにvault外の新しい作業フォルダを使う。

## 重複防止

`scripts/save_paper.py --check-only` で次の衝突を処理前に確認する。

- 同名Markdown
- 同名で内容のあるassetsフォルダ
- ファイルシステムへ保存できない `{SanitizedTitle}`

空のassetsフォルダは再利用する。保存時にも同じ簡易確認を行い、衝突時は上書きや自動サフィックス付与をせず中止する。

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
figure: "assets/{SanitizedTitle}/artifacts/image_001.png"
---
## Abstract

Abstractがある場合のみ原文……

## 原論文の最初の主要章

整形した原文……

## PDF

![[assets/{SanitizedTitle}/{SanitizedTitle}.pdf]]

## BibTeX

```bibtex
@inproceedings{author2026title,
  ...
}
```
````

必須frontmatterは `title`、`year`、`doi`、`authors`、`source`、`citekey` とする。Figure 1を特定できた場合は `figure` も追加する。`title`、`doi`、`source`、各著者名、`figure` は二重引用符で囲み、内部の二重引用符とバックスラッシュをYAML規則に従ってエスケープする。citekeyは小文字英数字の未引用文字列とする。年が不明なら `year: ""`、著者が不明なら `authors: []` とする。

参考文献一覧は保存しない。

## 保存

`scripts/save_paper.py` は見出し前後の空行と番号付き見出しの階層を整え、次を確認してから直接保存する。

- MarkdownとPDFが非0 byteである。
- artifacts内が非0 byteのPNGだけである。
- PDF埋め込みが期待するvault相対パスと一致する。
- 各画像埋め込みがartifacts内の画像を指す。
- `figure` がある場合は、artifacts内の非0 byte PNGを指す。
- 保存後のMarkdown、PDF、画像数が入力と一致する。

既存ファイルは変更しない。保存に失敗した場合は、その実行で新規作成した対象だけを除去する。

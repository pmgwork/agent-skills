# PDF 解析

PDF 解析は Docling だけを使う。本文抽出、Markdown 化、レイアウト構造、画像要素の検出は Docling の変換結果を基準にする。

## 実行方法

Docling は `uvx`（uv のワンショット実行）で起動する。事前の import 確認やバージョン確認は原則として行わない。

Docling 変換は 1 PDF につき 1 回だけ実行し、その出力を本文抽出と Figure 1 判定の両方に使う。入力 PDF と出力先は絶対パスで指定する。

```bash
uvx --from "docling-slim[standard]" docling "<input.pdf>" \
  --to md \
  --image-export-mode referenced \
  --device cpu \
  --no-ocr \
  --output "<work/docling>"
```

`docling` 実行ファイルは `docling-slim` が提供するため、`docling-slim[standard]`（フルの `docling` が内部依存する指定）を使う。`uvx --from docling docling` は警告が出て、uv が勧める `docling-slim` 単体は PDF 依存（`pypdfium2`、`docling_parse`）を欠き失敗するので、どちらも使わない。

各オプションの意味:

- `--to md`: Markdown を出力する。
- `--image-export-mode referenced`: 検出した図表を PNG として書き出し、Markdown から相対パスで参照する。
- `--device cpu`: MPS 由来の型エラーを避けるため、アクセラレータを CPU に固定する。
- `--no-ocr`: 既定では OCR を無効にする。Docling CLI の OCR は既定で有効なため、明示的に切る必要がある。
- `--output`: 出力ディレクトリ。

グローバル環境や利用者の Python へ `pip install docling` を直接実行しない。

## 出力

`--output <work/docling>` に対して、Docling CLI は次を書き出す。`<PDF名>` は入力 PDF のファイル名（拡張子を除いた部分）である。

- `<work/docling>/<PDF名>.md`: Docling 変換後の Markdown。
- `<work/docling>/<PDF名>_artifacts/`: `referenced` モードで書き出された図表 PNG 群。Markdown 内の画像参照はこのフォルダを指す。

以降、この Markdown を `docling.md` 相当として扱う。

## OCR

画像ベース PDF で通常抽出できない場合だけ、ユーザーに確認して `--ocr`（または `--force-ocr`）を有効にする。

```bash
uvx --from "docling-slim[standard]" docling "<input.pdf>" \
  --to md \
  --image-export-mode referenced \
  --device cpu \
  --ocr \
  --output "<work/docling>"
```

OCR は初回実行時に追加モデルや外部依存を要求する場合がある。OCR 結果に不確かな箇所がある場合は、推測で補わず、完了報告に不確実性を記載する。

## 本文抽出

要約とメタデータ抽出には出力された Markdown を優先して使う。本文の読み順、見出し、表、図の caption は Docling の出力を基準にする。

title、authors、source、year、doi は、Docling の Markdown と PDF 内に明示された情報から取得する。PDF 内に明示がない項目は推測で補わない。

## 作業ファイル

Docling の Markdown と `<PDF名>_artifacts/` の画像は作業用ファイルとして扱う。Obsidian vault へ登録する成果物は、最終 Markdown、PDF、抽出できた場合の `{SanitizedTitle}_figure1.png` だけにする。

# PDF解析

PDFの本文、構造、表、数式、画像はDoclingの変換結果を基準にする。PATH上の `docling` を使い、自動インストールや `uvx` へのフォールバックは行わない。

## OCRモード

次のコマンドで先頭3ページのテキスト有無を確認する。

```bash
python3 scripts/detect_pdf_text.py "<input.pdf>"
```

- 1文字以上取得できる: `no-ocr` とする。
- 0文字: `ocr` とする。
- `pdftotext` がない、または判定に失敗する: 確認せず既定の `no-ocr` とする。

`ocr` と判定した場合は、Doclingを実行する前にチャットで「OCRが必要なPDFです」と明示する。確認待ちにはせず、そのままOCR変換を続行する。

選択したモードでDoclingを1回だけ実行する。

```bash
docling convert "<input.pdf>" \
  --to md \
  --image-export-mode referenced \
  --device cpu \
  --no-ocr \
  --output "<work/docling>"
```

OCRを使う場合は `--no-ocr` を `--ocr` へ置き換える。

## 成功条件

入力が `<PDF名>.pdf` の場合、非空のMarkdownを必須とする。画像がある論文ではartifactフォルダも生成される。画像がなければartifactフォルダがなくてもよい。

```text
<work/docling>/
├── <PDF名>.md
└── <PDF名>_artifacts/  # 画像がある場合
    └── *.png
```

変換が異常終了した場合や重大な欠落がある場合は保存せず報告する。OCRモードの既定値を使うための確認は行わない。同じPDFへ別モードで再実行する必要が生じた場合だけユーザーへ確認する。全PNGを成果物として扱い、Figure 1だけの選別や結合は行わない。

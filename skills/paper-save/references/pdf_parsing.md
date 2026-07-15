# PDF解析

PDFの本文、構造、表、数式、画像はDoclingの変換結果を基準にする。出力Markdownと画像は要約材料ではなく、AI整形を経て最終ノートを構成する一次成果物として扱う。

## 事前確認

PATH上にインストール済みの `docling` を使う。見つからなければ自動インストールや `uvx` へのフォールバックをせず中止する。

```bash
if ! command -v docling >/dev/null 2>&1; then
  echo "docling がPATH上にありません。処理を中止します。" >&2
  exit 1
fi
```

DoclingのメジャーなCLI形状を確認し、`docling convert --help` が成功することを確認する。

## 1回だけ変換する

通常のテキストPDFではOCRを無効にする。

```bash
docling convert "<input.pdf>" \
  --to md \
  --image-export-mode referenced \
  --device cpu \
  --no-ocr \
  --output "<work/docling>"
```

画像ベースPDFであることが変換前に分かっている場合だけ、ユーザーの確認を得て `--no-ocr` を `--ocr` に置き換える。通常変換の結果を見てOCR付きで再実行してはならない。OCRの要否を判断できない場合は、実行前にユーザーへ確認する。

同じ入力PDFに対するDocling変換は、選択したOCRモードで1回だけ実行する。Doclingの絶対パスをスキルへ固定せず、グローバルPython環境へパッケージをインストールしない。

## 出力

入力が `<PDF名>.pdf` の場合、次を期待する。

```text
<work/docling>/
├── <PDF名>.md
└── <PDF名>_artifacts/
    └── *.png
```

- `<PDF名>.md` は画像参照の変換後、AIによる構造整形へ渡す。
- `<PDF名>_artifacts/` 内の全PNGを最終 `artifacts/` へ保存する。
- Figure 1だけを選別、複製、結合しない。
- DoclingのMarkdownや画像フォルダを、登録後に削除される作業パスから直接リンクしない。

変換後にMarkdownとartifactフォルダが存在することを確認する。Markdownが空、変換が異常終了、または抽出結果に重大な欠落がある場合は登録せず報告する。

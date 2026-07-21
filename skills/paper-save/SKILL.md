---
name: paper-save
description: 論文PDFをDoclingで抽出し、AIで論文構造と読み順を整えた原文、全画像、原本PDF、BibTeXをObsidian vaultへ保存するときに使う。要約や翻訳をせず、論文を新規登録・アーカイブする依頼に適用する。
---

# Paper Save

論文PDFの内容を意味を変えずに読みやすい構造へ復元し、全画像、原本PDF、BibTeXとともにObsidian vaultへ保存する。日本語要約、翻訳、評価、タグ、関連論文推薦は生成しない。

## ワークフロー

1. 保存先と重複を確認する。
2. PDFをDoclingで1回だけ変換する。
3. 公式メタデータを照合し、frontmatterとBibTeXを確定する。
4. 画像参照を機械変換する。
5. AIで論文構造と読み順を整形する。
6. 参考文献の作品タイトルをObsidian内部リンクにする。
7. 最終Markdownの見出し前後を機械整形する。
8. Markdown、原本PDF、全画像をvaultへ保存する。
9. 保存結果を読み戻して検証する。

## 1. 保存先と重複の確認

vaultルートの解決、保存構造、重複時の停止条件は `references/registration.md` に従う。書き込み前にMarkdownとPDFの両方を確認する。同名ノートまたは同名PDFがあれば上書きも自動サフィックス付与もせず、処理を中止する。

`{SanitizedTitle}`、artifact名、Obsidianリンク、BibTeX keyは `references/naming.md` に従う。

## 2. Docling変換

コマンドと出力の扱いは `references/pdf_parsing.md` に従う。

- PATH上の `docling` だけを使う。見つからなければ中止する。
- 変換前にOCRの要否を判断し、選択したモードで1回だけ実行する。
- 同じPDFにDoclingを再実行しない。
- Markdownと全画像を最終成果物として扱う。

## 3. メタデータとBibTeX

タイトル、年、DOI、著者、掲載先、citekey、BibTeXの取得・補完は `references/metadata.md` に従う。日本語タイトル、rating、tagsは作らない。

## 4. 画像の後処理

Docling変換後、`scripts/postprocess_docling.py` を1回実行する。

```bash
python3 scripts/postprocess_docling.py \
  --markdown "<work/docling>/<PDF名>.md" \
  --artifacts-dir "<work/docling>/<PDF名>_artifacts" \
  --output-markdown "<work/final/prepared.md>" \
  --output-artifacts-dir "<work/final/artifacts>" \
  --asset-link-prefix "assets/{SanitizedTitle}/artifacts"
```

このスクリプトは次を行う。

- Markdown本文中の画像を初出順に `image_001.png` から採番する。
- 同じ画像の重複参照には同じ連番を使う。
- 未参照の画像もファイル名順で後続番号に採番する。
- 画像参照をObsidian埋め込みへ置換する。
- Doclingの文章と見出しは変更せず、次のAI整形工程へ渡す。
- 変換できないローカル画像参照、PNG以外のartifact、空でない出力先があれば失敗する。

## 5. AIによる構造整形

`prepared.md` を入力として、`references/content_formatting.md` に従い論文構造と読み順を復元する。章名を標準的な構成へ置き換えず、原論文に存在する見出し名、順序、相対階層を保持する。

## 6. 参考文献の内部リンク化

参考文献一覧がある場合は `references/reference_links.md` に従い、一覧全体を番号付きの作品タイトル内部リンクへ置き換える。本文中の `[1]` などの引用記号と番号が対応するようにする。

## 7. 最終Markdownの機械整形

frontmatter、AI整形済み本文、PDF埋め込み、BibTeXを作業用の最終ノートへまとめた後、`scripts/format_final_markdown.py` を1回実行する。

```bash
python3 scripts/format_final_markdown.py \
  --input "<work/final/note.md>" \
  --output "<work/final/note-formatted.md>"
```

このスクリプトはYAML frontmatterとコードフェンスの内容を変更せず、frontmatter直後の最初のATX見出しは空行を挟まず配置し、それ以外のATX見出しの前とすべてのATX見出しの後へ空行を1行ずつ確保する。vaultへ保存するのは `note-formatted.md` とする。

## 8. Obsidian登録

frontmatter、本文テンプレート、ファイルコピー、検証は `references/registration.md` に従う。AI整形した本文を保存し、`<work/final/artifacts>` の全画像をvaultの対応フォルダへコピーする。

既存の論文ノートは編集しない。`paper-summary` の既存要約ノートを移行しない。

## 9. 完了報告

次を簡潔に報告する。

1. 正式英語タイトル
2. 作成したノートのパス
3. 保存したPDFのパス
4. 保存した画像数とartifactsフォルダのパス
5. BibTeX key
6. 公式メタデータで補完できなかった項目
7. 内部リンク化できなかった参考文献の有無
8. 検証結果

## 参照ファイル

- `references/pdf_parsing.md`: Doclingの実行と出力規則。
- `references/content_formatting.md`: AIによるノイズ除去、読み順復元、見出し正規化の規則。
- `references/metadata.md`: 公式メタデータ照合とBibTeXの作成規則。
- `references/naming.md`: ファイル、artifact、リンク、citekeyの命名規則。
- `references/reference_links.md`: 参考文献タイトルのObsidian内部リンク化規則。
- `references/registration.md`: vault登録、ノート形式、重複防止、検証項目。

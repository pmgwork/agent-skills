---
name: paper2obsidian
description: 論文PDFをMarkerで抽出し、原文Markdown・図・表・原本PDF・BibTeXをObsidianへ保存する。参考文献を論文ノートへのリンクにし、本文の引用番号からReferencesへ移動できる形にする。処理はスクリプト1本で行い、エージェントは書誌データが取れない場合だけ補う。論文保存やテスト変換に使う。
---

# paper2obsidian

PDFの原文を要約・翻訳せずにMarkdown化して保存する。変換・書誌データ取得・リンク・保存・保存後の検査は `scripts/run.py` が1回で行う。Markerの抽出結果はそのまま使い、図の分割や読み順の乱れなどの小さな誤りは直さない。本文の通読や原本との照合はしない。

## 準備

- 保存先は環境変数 `PAPER_SAVE_VAULT_ROOT`。未設定なら設定を依頼し、保存を進めない。テスト保存の依頼では空の作業用Vaultを作り `--vault-root "<test-vault>"` を付ける。元のVaultは変更しない。
- Marker（`uv tool install marker-pdf`）が必要。スクリプトはMarkerと同じPythonで実行する。`scripts/` はこのスキルからの相対パス。
- 文字化けするPDFやスキャンPDFのOCRには llama.cpp の `llama-server` が必要（PATH上、または環境変数 `LLAMA_CPP_BINARY`）。

```bash
PY="$(sed -n '1s/^#!//p' "$(command -v marker_single)")"
"$PY" scripts/run.py "<input.pdf>" --work "<新しい作業ディレクトリ>"
```

論文のDOIが1ページ目に印刷されていない場合は `--doi`、ネットワークを使わない場合は `--offline` を付ける。

## 結果

- **終了コード0（`"status": "saved"`）**: 保存と検査まで完了している。ノートを読み直さず、出力JSONから報告する。
- **終了コード2（`"status": "review"`）**: `<work>/review.md` の項目を `<work>/draft.md` に1回で反映し、`"$PY" scripts/run.py --work "<work>" --resume` で保存する。
  - **metadata**: Crossrefに記録がない。まず `draft.md` の冒頭を1ページ目の画像と見比べ、単語が途中で切れるなど本文が崩れていれば、PDFの文字データが壊れているので、frontmatterを書かずに新しい作業ディレクトリで `--ocr always` を付けて実行し直す。崩れていなければ、1ページ目の画像から frontmatter（`title`・`authors`・`year`・`doi`・`source`・`citekey`）を書き、末尾に `## PDF`（`[Original PDF](<assets/{SanitizedTitle}/{SanitizedTitle}.pdf>)`）と `## BibTeX`（コードブロック）を足す。`title` は保存名にも使う。`citekey` は第一著者姓＋年＋タイトル先頭語（a/an/theを除く）。保存名は `scripts/paper_common.py` の `sanitize_title()` で求める。不明な値は創作しない。
  - **text**: OCRが必要だが実行できなかった。ユーザーに llama.cpp の導入を依頼し、本文は直さない。
- **終了コード1**: エラー。同名ノートが既にある場合も停止するので、退避・削除はユーザーの指示に従う。

報告は、ノートのパス、`citekey`、図の保存数（`images`）、参考文献の既存/未保存/リンクなしの件数を簡潔に示す。`problems` が空でなければその内容を、`unlinked_with_reason`・`missing_numbers`・`duplicate_numbers` があれば一言添える。直す必要はない。

## 処理の中身

- 変換: PDFの文字データで変換し、"�"（文字化け）・文字データなし・語の2割以上の欠落のいずれかの場合だけOCRでやり直す。
- 書誌データ: 最初の2ページのDOI、なければ題名で Crossref を検索し、題名が原本と一致した記録から frontmatter・`## PDF`・`## BibTeX` を作る。サムネイル（`figure`）は本文で最初の、ある程度大きい画像。
- References: 番号付き（`[1]`、`1.`）の参考文献だけ1項目1行にして `^ref-N` を付け、本文の `[53]` を項目へのリンクにする。DOIの登録題名が原文にある項目は論文ノートへのリンクにする。番号のない形式はMarkerの出力のまま残す。詳細は [references/linking.md](references/linking.md)。
- 保存後の検査: 画像・PDF・サムネイルの参照先が存在し、作業ディレクトリへの参照が残っていないこと。

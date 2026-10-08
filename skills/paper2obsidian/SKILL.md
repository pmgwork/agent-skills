---
name: paper2obsidian
description: 論文PDFをDoclingで抽出し、エージェントが原本と照合・修正して、原文Markdown・図・表・原本PDF・BibTeXをObsidianへ保存する。参考文献を論文ノートへのリンクにし、本文の引用番号からReferencesへ移動できる形にする。論文保存やテスト変換に使う。
---

# paper2obsidian

PDFの原文を要約・翻訳せずにMarkdown化する。Doclingの出力を下書きとし、崩れやすい箇所（図・表・数式・参考文献）だけを原本と照合して直す。本文全体の再転記や全ページの目視照合はしない。機械的な処理は付属スクリプトに任せる。

## 準備

- 保存先は環境変数 `PAPER_SAVE_VAULT_ROOT`。未設定なら設定を依頼し、保存を進めない。テスト保存の依頼では空の作業用Vaultを作ってよく、元のVaultは変更しない。
- スクリプトはDoclingと同じPython（`pypdfium2` が入っている）で実行する。`scripts/` はこのスキルからの相対パス。

```bash
PY="$(sed -n '1s/^#!//p' "$(command -v docling)")"   # uv tool の場合。動かなければ pypdfium2 のある python3
```

保存構造:

```text
<Vault>/papers/{SanitizedTitle}.md
<Vault>/papers/assets/{SanitizedTitle}/{SanitizedTitle}.pdf
<Vault>/papers/assets/{SanitizedTitle}/artifacts/image_001.png
```

## 1. 抽出と下書き

```bash
docling convert "<input.pdf>" --to md --to json --image-export-mode referenced \
  --device cpu --no-ocr --output "<work>/extracted"
"$PY" scripts/triage.py --markdown "<work>/extracted/<name>.md" --json "<work>/extracted/<name>.json" \
  --pdf "<input.pdf>" --output "<work>/triage"
```

テキストのないスキャンPDFには `--ocr` を使う。Doclingが使えない場合は制約を報告する。`triage.py` は次を作る。DoclingのJSONは大きいので直接読まない。

- `note-draft.md`: References節を除き、画像参照を絶対パスにした下書き
- `references.draft.json`: 参考文献の番号・原文（`raw`）・推定タイトル・年・第一著者・DOI
- `triage.json`: 照合が必要な図・表・数式のページと座標（左, 上, 右, 下。pt）、キャプション
- `pages/`: 1ページ目と照合対象ページの画像

正式タイトルを確認したら、`save_paper.py --check-only`（下記）で重複を確認してから作業を進める。

## 2. 照合と修正

`note-draft.md` を一度通読し、`triage.json` の項目を `pages/` の画像で確認する。

- **メタデータ**: 1ページ目から正式タイトル、著者、年、DOI、掲載先を確認してYAML frontmatterに書く。`citekey` は第一著者姓＋年＋タイトル先頭語（a/an/theを除く）。不明な値は創作しない。
- **図**: キャプションとの対応と、複数パネルの欠落を確認する。欠落・分割・余分な領域がある図だけ、`triage.json` の座標を基に切り出し直し、`![Figure 1](<絶対パス>)` で参照する。Figure 1 を特定できたら frontmatter の `figure` に同じ画像パスをJSON形式の引用符付きで設定する。

  ```bash
  echo '[{"page": 1, "bbox": [54, 275, 558, 528], "file": "figure-01.png"}]' > "<work>/figures.json"
  "$PY" scripts/prepare_pdf.py "<input.pdf>" --figures "<work>/figures.json" --output "<work>/figures"
  ```

- **表・数式**: 崩れたセル・数式だけ原本どおりに直す。Markdownで表せない構造はHTML表か画像で保持し、不確かな値は補完しない。`<!-- formula-not-decoded -->` は原本から転記する。
- **本文**: 通読で段組みの混入、段落の途中切れ、改行による単語分割を見つけた箇所だけ、`"$PY" scripts/prepare_pdf.py "<input.pdf>" --pages 3,4 --output "<work>/pages"` で該当ページを見て直す。見出し階層・脚注・謝辞・Appendixを保持し、原文の誤字らしきものは訂正しない。ページヘッダー・フッター、著作権定型文、重複する所属・メールは除く。
- **末尾**: `## PDF` の下に `[Original PDF](<assets/{SanitizedTitle}/{SanitizedTitle}.pdf>)`、`## BibTeX` の下にコードブロックを付ける。保存名は `scripts/paper_common.py` の `sanitize_title()` で求め、別の規則で命名しない。

## 3. 引用とReferences

`references.draft.json` の各項目を `raw` と照合し、推定タイトルの誤りを直して `references.json` として保存する。論文以外は `kind` を変更して `url` または `citation` を付ける。番号は原本のまま保持する。入力形式と照合規則は [references/linking.md](references/linking.md) を参照する。

```bash
"$PY" scripts/link_references.py --markdown "<work>/triage/note-draft.md" \
  --references "<work>/references.json" --output "<work>/note.md"
```

本文の `[53]` は `\[ [[#^ref-53|53]] \]`、Referencesは `53. [[papers/サニタイズ済みタイトル|原題]] ^ref-53` になる。未保存の論文には予定のノート名へのリンクだけを作り、空ノートや引用先PDFを作成・取得しない。複数候補や名前衝突はスクリプトの報告を見て、原本・既存ノートと照合して解決する。テスト用Vaultを参照する場合は `--vault-root "<test-vault>"` を付ける。

## 4. 保存と確認

```bash
"$PY" scripts/save_paper.py --title "<Official Title>" --pdf "<input.pdf>" --markdown "<work>/note.md" --check-only
"$PY" scripts/save_paper.py --title "<Official Title>" --pdf "<input.pdf>" --markdown "<work>/note.md"
```

本文から参照された画像だけが保存される。参照していないDocling画像も残す場合は `--artifacts <画像だけのディレクトリ>` を付ける。テスト保存ではこれらのコマンドに限って `PAPER_SAVE_VAULT_ROOT="<test-vault>"` を指定する。既存ノートや同名アセットフォルダがあれば上書きせず停止するので、退避・削除はユーザーの指示に従う。

保存後にノートを読み直し、PDF・図の参照先、サムネイル、`#^ref-N` と `^ref-N` の対応、一時ディレクトリへの参照が残っていないことを確認する。完了報告はノートのパス、図の保存数、参考文献の既存/未保存リンク数、citekey、照合していない箇所を簡潔に示す。

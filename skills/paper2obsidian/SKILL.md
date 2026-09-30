---
name: paper2obsidian
description: 論文PDFをDoclingで抽出し、エージェントが原本と照合・修正して、原文Markdown・図・表・原本PDF・BibTeXをObsidianへ保存する。参考文献を論文ノートへのリンクにし、本文の引用番号からReferencesへ移動できる形にする。論文保存やテスト変換に使う。
---

# paper2obsidian

PDFの原文を要約・翻訳せずにMarkdown化する。DoclingのMarkdown・構造JSON・画像を下書きとして使い、エージェントが原本と照合して修正する。本文全体の再転記を標準にせず、抽出が崩れた箇所を補修する。引用リンク生成と保存は付属スクリプトに任せる。

## 保存先と準備

通常の保存は環境変数 `PAPER_SAVE_VAULT_ROOT` を使用する。未設定なら設定を依頼し、Vaultへの保存を進めない。テスト保存の依頼では空の作業用Vaultを作り、そちらへ保存してよい。元のVaultを変更しない。

保存構造:

```text
<Vault>/papers/{SanitizedTitle}.md
<Vault>/papers/assets/{SanitizedTitle}/{SanitizedTitle}.pdf
<Vault>/papers/assets/{SanitizedTitle}/artifacts/image_001.png
```

Doclingを使用する。原本の画像確認・補助切り出しには `pdfplumber` と `pypdfium2` を使い、利用可能なら環境のバンドル済みPythonを選ぶ。命令中の `scripts/` はこのスキルからの相対パスである。

表紙から正式タイトルを確認したら、抽出前に下記の `save_paper.py --check-only` で重複を確認する。保存直前にも再確認する。

一時ディレクトリにDoclingの下書きを一度だけ出力する:

```bash
docling convert "<input.pdf>" --to md --to json \
  --image-export-mode referenced --device cpu --no-ocr \
  --output "<work>/extracted"
```

テキストのないスキャンPDFには `--ocr` を使う。抽出MarkdownとJSON、生成された画像ディレクトリを確認し、元の出力は保持して `note-draft.md` で修正する。Doclingが使えない場合は制約を報告し、原本からの手動組み立てを代替とする。

原本のページ画像を作り、抽出結果と照合する:

```bash
python3 scripts/prepare_pdf.py "<input.pdf>" --output "<work>/prepared"
```

`pages/page-001.png` と `pdf-text.json`（ページ寸法、文字・単語の座標、画像の領域）が得られる。抽出結果を通読し、ページ画像で配置を確認する。段組み・ページ境界・図キャプション・表・数式を重点的に照合し、疑わしい領域だけ拡大して修正する。DoclingのJSONの座標・構造情報を使って原本の位置を追う。読めない部分を推測で補わない。

## 原本からノートを組み立てる

- 原本の正式タイトル、著者、年、DOI、掲載先、citekeyを確認してYAML frontmatterに記載する。`citekey` は第一著者姓＋年＋タイトル先頭語（a/an/theを除く）を基本にする。不明なメタデータは創作しない。
- 左右の段とページ境界を確認して段落をつなぐ。本文、手順、箇条書きの順序を保持し、図・表の浮動配置によって文章を分断しない。
- 見出し階層、数式、表、脚注、謝辞、Appendixと参考文献を保持する。原文の誤字らしきものも勝手に訂正しない。ページヘッダー・フッター、著作権定型文、著者ごとの重複所属・メールアドレスは除外する。
- 改行に伴う単語分割と本来のハイフンを区別する。本文の引用番号は原本の番号で保持し、文献を並べ替えて番号を振り直さない。
- 表はDoclingの出力を原本のセル対応と照合し、崩れたセルだけ修正する。Markdownでは表現できない構造はHTML表か画像で保持し、不確かな数値や数式を補完しない。
- 毎回PDF固有の変換コードを作らない。Doclingの下書きと付属の準備・切り出しツールを使い、読み順・段落・構成の修正はエージェントが判断する。

図はDoclingが抽出した画像を優先し、キャプションとの対応と複数パネルの欠落を確認する。欠落・分割・余分な領域がある図だけ、付属ツールで原本から切り出す。図の領域を原本のPDF座標（左、上、右、下。単位pt）で `figures.json` に記載して切り出す。画像は図全体を含め、複数パネルの欠落がないことを確認する。キャプションは本文とは別に転記する。

```json
[{"page": 1, "bbox": [54, 275, 558, 528], "file": "figure-01.png"}]
```

```bash
python3 scripts/prepare_pdf.py "<input.pdf>" \
  --figures "<work>/figures.json" --output "<work>/figures"
```

`note-draft.md` は抽出Markdownを基に作り、Doclingの元画像参照を維持する。補助切り出しの画像には `![Figure 1](figures/figure-01.png)` のようなローカル画像参照を使う。画像の手動採番は不要。Figure 1を特定できた場合はfrontmatterの `figure` に同じ元画像パスをJSON形式の引用符付きで設定する。PDFは `## PDF` の下に `[Original PDF](<assets/{SanitizedTitle}/{SanitizedTitle}.pdf>)`、BibTeXは `## BibTeX` の下にコードブロックとして付ける。保存名は `scripts/paper_common.py` の `sanitize_title()` で求め、LLMが別の規則で命名しない。

## 引用とReferences

抽出した参考文献を原本と照合し、構造化した `references.json` を作り、`note-draft.md` にはReferences節を含めない。配列の番号は原本のまま保持する。項目の分類・タイトル抽出・DOI確認はエージェントが行う。入力形式、照合と例外は [references/linking.md](references/linking.md) を読む。

```bash
python3 scripts/link_references.py \
  --markdown "<work>/note-draft.md" --references "<work>/references.json" \
  --output "<work>/note.md"
```

テスト用のVaultを参照する場合は `--vault-root "<test-vault>"` を付ける。既存ノートを照合するだけなら本来のVaultを読み、出力は作業ディレクトリに置いてよい。

本文の `[53]` は `\[ [[#^ref-53|53]] \]` に、Referencesは次の形になる:

```md
53. [[papers/サニタイズ済みタイトル|原題]] ^ref-53
```

本文の番号→Referencesの該当項目→論文ノートの順に移動できる。論文以外のWebサイト・動画・作品などは元URLへのMarkdownリンクにする。原本にURLがない書籍等は原文の書誌情報をテキストとして保持する。未保存の論文には予定のノート名へのリンクだけを作り、空ノートや引用先PDFを自動作成・取得しない。

保存とリンク生成は同じサニタイズ関数を使用する。既存ノートはDOIを優先し、タイトル等で一意に照合できた実ファイル名を使う。複数候補や名前衝突はスクリプトの報告を確認し、原本・既存ノートを照合して解決する。推測で別論文へつながない。

## 保存と確認

保存前に原本と本文の順序、ページ境界、図とキャプション、表、脚注、引用番号を照合する。確認していない箇所は区別して報告する。正規化した文字列の存在確認だけで全文の忠実性を保証しない。

```bash
python3 scripts/save_paper.py --title "<Official Title>" \
  --pdf "<input.pdf>" --markdown "<work>/note.md" --check-only
python3 scripts/save_paper.py --title "<Official Title>" \
  --pdf "<input.pdf>" --markdown "<work>/note.md" --artifacts "<extracted-image-directory>"
```

`--artifacts` には図の画像だけを含むディレクトリを指定する（実際の出力名を確認し、推測しない）。Doclingが同じ場所に `page_*.png` のページ全体画像も出力した場合は、図の `image_*.png` を別ディレクトリへまとめてから指定する。コピーした場合は本文とfrontmatterの画像参照もコピー先へ揃え、同じ画像が元ファイルとコピーから二重保存されないようにする。ページ全体画像は原本照合用として作業ディレクトリに保持する。補助切り出し画像は本文のローカル参照からも収集される。

テスト保存ではこれらのコマンドに限って `PAPER_SAVE_VAULT_ROOT="<test-vault>"` を指定する。既存ノートや同名アセットフォルダ（空でも）があれば上書きせず停止する。既存ファイルの退避・削除は保存依頼から推測せず、ユーザーの指示に従う。保存はアセットのコピー完了後にノートを公開する。中断後にアセットだけ残った場合も競合として停止する。

保存後にノートを読み直し、PDF・図の参照先、サムネイル、本文の `#^ref-N` とReferencesの `^ref-N` の対応を確認する。未保存論文への予定リンクは欠損アセットと区別する。一時ディレクトリの参照を残さない。

完了報告はノートのパス、PDF・図の保存結果、参考文献の既存/未保存リンク数、citekey、未確認箇所を簡潔に示す。

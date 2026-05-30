# Obsidian 登録

## vault ルートの解決

保存先フォルダはユーザー指定がない限り `papers`。保存先 vault は、特に指定がなければ現在アクティブな（最後にフォーカスした）vault とする。vault ルート（以下 `<VAULT_ROOT>`）は Obsidian CLI で取得する。

```bash
obsidian vault info=path
```

別の vault に保存したい指定がある場合は、`obsidian vaults verbose`（各行が「名前<TAB>絶対パス」）の一覧から、その vault 名の行のパスを使う。

```bash
obsidian vaults verbose
```

書き込みは、本文 `.md` を Write で直接作成し、PDF と Figure 1 画像を `<VAULT_ROOT>` 配下へコピーする。バイナリ資産や長い構造化ノートを `obsidian create` で流し込まない。CLI は vault パスの解決と、後述の検証・オープンに限定して使う。

```text
<VAULT_ROOT>/papers/{SanitizedTitle}.md
<VAULT_ROOT>/papers/assets/{SanitizedTitle}/{SanitizedTitle}.pdf
<VAULT_ROOT>/papers/assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png
```

`papers` フォルダと `papers/assets/{SanitizedTitle}` フォルダがなければ作成する。

## タイトルのサニタイズ

`{SanitizedTitle}` は `references/naming.md` に従って作成する。Markdown 名、PDF 名、PDF 用フォルダ、PDF 埋め込みリンク、Figure 1 リンク、Obsidian ノートリンクで同じ値を使う。

## 重複回避

既存ファイルがある場合は、ユーザーから上書き指示がない限り上書きしない。

書き込み前に、同名ノートの有無を確認する。Obsidian CLI が使えれば、ファイルシステムの存在確認に加えて次でも調べられる。

```bash
obsidian read path="papers/{SanitizedTitle}.md"   # 既存なら本文が返る
```

同名ノートまたは同名 PDF が存在する場合は、`references/naming.md` の重複時ルールに従い、Markdown、PDF、PDF 用フォルダ、Figure 1 画像、Obsidian リンクのすべてで同じ識別子付きタイトルを使う。

## frontmatter

```yaml
---
year: 出版年
doi: "https://doi.org/..."
tags:
  - paper/tag1
  - paper/tag2
authors:
  - "著者1 (MIT)"
  - "著者2 (Stanford)"
source: "ジャーナル名, Vol. X, No. Y, pp. Z-W"
rating: "★★"
figure: "assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png"
---
```

`figure` は Figure 1 を抽出できた場合のみ作成する。

## 本文テンプレート

Figure 1 を抽出できた場合は、frontmatter 直後、タイトル見出しの前に画像を入れる。抽出できない場合は、この画像埋め込みを作らない。

````markdown
![[assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png]]

## 抽出した日本語タイトル

### どんなもの？

...

### 先行研究と比べてどこがすごい？

...

### 技術や手法のキモはどこ？

...

### どうやって有効だと検証した？

...

### 議論はある？

...

### 次に読むべき論文は？

...

### 論文PDF

![[assets/{SanitizedTitle}/{SanitizedTitle}.pdf]]

### BibTeX

```bibtex
@article{...}
```
````

## 保存後の検証

作成した Markdown ファイルを読み戻し、以下を確認する。

- 文字化け、欠落、frontmatter の崩れがない。
- PDF リンク、Figure 1 リンク、BibTeX が欠落していない。
- BibTeX key がすべて小文字で、`references/naming.md` の規則に従っている。
- Markdown ファイル名、PDF ファイル名、PDF 用フォルダ名、PDF 埋め込みリンク、Figure 1 リンクに使われている `{SanitizedTitle}` が完全一致している。
- PDF ファイルが存在し、サイズが 0 byte ではない。
- Figure 1 を保存した場合は、PNG ファイルが存在し、サイズが 0 byte ではなく、frontmatter の `figure` および本文冒頭の埋め込みリンクと一致している。

Obsidian CLI が使える場合は、読み戻しと最終提示にも利用してよい。

```bash
obsidian read path="papers/{SanitizedTitle}.md"   # 登録結果の確認
obsidian open path="papers/{SanitizedTitle}.md"   # 登録ノートを利用者に提示
```

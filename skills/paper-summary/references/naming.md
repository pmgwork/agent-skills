# 命名規則

論文ノート登録で使う名前は、このファイルの規則に従って一貫させる。対象は Markdown ファイル名、PDF ファイル名、assets フォルダ名、Figure 1 画像名、Obsidian リンク、関連論文リンク、BibTeX key である。

## SanitizedTitle

英語タイトルから `{SanitizedTitle}` を一度だけ生成し、ファイル名、PDF フォルダ名、PDF ファイル名、Obsidian 埋め込みリンク、Obsidian ノートリンク、関連論文リンクに必ず同じ値を使う。原題や日本語タイトルをそのままファイル名・フォルダ名・リンク先に使わない。

作成順序:

1. 英語の正式タイトルを原題どおりに取得する。
2. `/ \ * ? " < > |` を削除する。
3. `:`, `-`, `–`, `—` などの区切り記号は、語が連結しないように半角スペースへ置換する。
4. ピリオド、カンマ、アポストロフィ、引用符、括弧類は、ファイル名として問題がない場合でも原則として削除する。
5. 連続する空白を半角スペース 1 個にまとめる。
6. 先頭と末尾の空白を削除する。
7. 大文字小文字は原題のまま保持する。
8. タイトルが長すぎる場合は、主要語が残る範囲で短縮し、短縮後にも上記の規則を再適用する。

一致確認:

- `papers/{SanitizedTitle}.md`
- `papers/assets/{SanitizedTitle}/`
- `papers/assets/{SanitizedTitle}/{SanitizedTitle}.pdf`
- `papers/assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png`
- `![[assets/{SanitizedTitle}/{SanitizedTitle}.pdf]]`
- `figure: "assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png"`
- `![[assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png]]`
- `[[{SanitizedTitle}|{Title}]]`

同名ノートまたは同名 PDF が存在する場合は、サニタイズ済みタイトルの末尾へ半角スペースと識別子を追加した `{SanitizedTitleWithSuffix}` を作成し、Markdown、PDF、PDF 用フォルダ、Figure 1 画像、Obsidian リンクのすべてで同じ `{SanitizedTitleWithSuffix}` を使う。識別子を追加した後も、空白や使用禁止文字がないか確認する。

例:

| Official Title | SanitizedTitle |
| --- | --- |
| `ModulAR: Eye-controlled vision augmentations for head mounted displays` | `ModulAR Eye-controlled vision augmentations for head mounted displays` |
| `ShipShape: A Drawing Beautification Assistant` | `ShipShape A Drawing Beautification Assistant` |
| `Toolglass and Magic Lenses: The See-Through Interface` | `Toolglass and Magic Lenses The See-Through Interface` |

## BibTeX key

BibTeX key は必ずすべて小文字にする。英大文字、空白、句読点、記号、日本語を含めない。

標準形式:

```text
{first_author_last_name}{year}{first_title_word}
```

作成順序:

1. 第一著者の姓をローマ字または英字表記で取得する。粒度のある姓はスペースや記号を削除して 1 語にする。
2. 出版年を 4 桁で付ける。
3. 英語タイトルの最初の意味語を 1 語付ける。冠詞 `a`, `an`, `the` は飛ばす。記号や句読点は削除する。
4. 全体を小文字にする。
5. `[^a-z0-9]` に該当する文字を削除する。

例:

| Author / Year / Title | BibTeX key |
| --- | --- |
| `Jane Smith`, `2024`, `ModulAR: Eye-controlled...` | `smith2024modular` |
| `Taro Yamada`, `2021`, `A Survey of Mid-Air Gesture Interaction` | `yamada2021survey` |
| `van der Waals`, `2020`, `The Effect of ...` | `vanderwaals2020effect` |

重複時:

- 同じ key が既存ノート内または同じ出力内に存在する場合は、末尾に `a`, `b`, `c` の順でサフィックスを付ける。
- サフィックスを付けた後も小文字英数字だけにする。

例:

```bibtex
@inproceedings{smith2024modular,
  author = {...},
  title = {...},
  year = {2024},
  booktitle = {...}
}
```

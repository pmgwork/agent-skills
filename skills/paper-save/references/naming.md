# 命名規則

## SanitizedTitle

正式英語タイトルから `{SanitizedTitle}` を1回だけ生成し、Markdown名、PDF名、assetsフォルダ名、リンクで同じ値を使う。

1. `/ \\ * ? " < > |` を削除する。
2. `:`, `-`, `–`, `—` は半角スペースへ置換する。
3. ピリオド、カンマ、アポストロフィ、引用符、括弧類を削除する。
4. 連続空白を半角スペース1個へまとめ、先頭と末尾の空白を削除する。
5. 大文字小文字は正式タイトルのまま保持する。
6. 内容を省略、要約、短縮しない。

生成した名前がファイルシステムの1要素として保存できない長さの場合は、自動短縮せず登録を中止して報告する。

次が完全一致しなければならない。

```text
papers/{SanitizedTitle}.md
papers/assets/{SanitizedTitle}/
papers/assets/{SanitizedTitle}/{SanitizedTitle}.pdf
![[assets/{SanitizedTitle}/{SanitizedTitle}.pdf]]
```

## artifacts

Doclingが書き出した全PNGを次へ保存する。

```text
papers/assets/{SanitizedTitle}/artifacts/image_001.png
papers/assets/{SanitizedTitle}/artifacts/image_002.png
```

- 本文に参照がある画像を初出順で採番する。
- 同一画像が複数回参照されても同じ番号を使う。
- 本文から参照されない画像は、元ファイル名の辞書順で後続番号を付ける。
- 桁数は最低3桁とし、1000枚以上では必要な桁数へ自然に拡張する。
- 本文のリンクは `![[assets/{SanitizedTitle}/artifacts/image_001.png]]` とする。
- Doclingの元ファイル名や作業ディレクトリを最終Markdownへ残さない。

## BibTeX key

標準形式は `{first_author_last_name}{year}{first_title_word}` とする。

1. 公式メタデータに英字表記の第一著者姓があればそれを使い、空白と記号を削除する。英字表記がなければ `unknown` を使い、独自に翻字しない。
2. 4桁の出版年を付ける。不明な場合は `nodate` を使う。
3. 正式英語タイトルを空白で分割し、先頭から `a`, `an`, `the` だけを飛ばした最初の英数字を含む語を付ける。それ以外のstop word判定は行わない。
4. 全体を小文字化し、`[^a-z0-9]` を削除する。
5. 第一著者が不明なら `unknown` を使う。

例: `smith2026modular`、`unknownnodateinteraction`

既存ノートに同じkeyがある場合は自動変更せず、登録を中止して衝突を報告する。

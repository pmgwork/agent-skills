# 見出し構造と読み順

`prepared.md` の見出しレベルを信用せず、原本PDFの全ページを視覚確認してから本文を整形する。見出し構造はAI出力後に推測し直さず、先に作る `heading-map.json` を正とする。

## PDFから見出し設計図を作る

PDFをページ画像として全ページ確認し、作業フォルダへ次の形式で `heading-map.json` を作る。

```json
{
  "headings": [
    {"level": 2, "title": "Abstract", "page": 1, "first_text": "This paper..."},
    {"level": 2, "title": "RESULTS", "page": 4, "first_text": "Participants..."},
    {"level": 3, "title": "Finding One", "page": 4, "first_text": "The first..."}
  ]
}
```

`level` と `title` は検証に使う必須項目とする。`page` と `first_text` は段組みの読み順と見出し位置を確認する作業用手掛かりとして記録する。

- 原論文の最上位章をlevel 2、その小節をlevel 3、小々節をlevel 4として相対階層を記録する。
- 番号付き見出しは `2` → level 2、`2.1` → level 3、`2.1.1` → level 4とする。
- 番号がない場合は、文書全体で一貫するフォントサイズ、太さ、大文字小文字、字下げ、前後余白と意味上の包含関係を合わせて判断する。大文字かTitle Caseかだけで決めない。
- 見出し番号、綴り、大文字小文字をPDFのまま記録し、存在しない番号や章名を追加しない。
- Abstractが存在する場合は `## Abstract` として先頭へ含める。最終ノート用の `PDF` と `BibTeX` はmapへ含めない。
- Figure/Table caption、図中や表中のラベル、著者名、柱、ページ番号、箇条書きのラベルを見出しへ含めない。
- 判定できない階層があれば保存を進めず、該当ページと候補をユーザーへ示す。

## 多段組みの読み順を固定する

- ページ上の列と座標を確認し、各見出しを直後に属する本文の前へ置く。
- 抽出順だけを根拠に、右列の見出しを左列本文より前へ移動しない。
- `first_text` と最終Markdownの見出し直後の本文を照合する。
- 本文のない孤立見出しがあれば、図中ラベルの誤認または段組み順序の誤りを疑い、PDFへ戻る。
- 主要章直後に小節が始まる構成は許容する。隣接見出しだけを理由に削除しない。

## 最終Markdownと照合する

機械整形後、次を実行する。

```bash
python3 scripts/validate_heading_structure.py \
  --markdown "<work/final/note-formatted.md>" \
  --expected "<work/final/heading-map.json>"
```

この検証はコードフェンス内と末尾の `## PDF`、`## BibTeX` を除外し、PDF由来の見出しについて文字列、順序、階層、個数の完全一致を要求する。失敗した場合はMarkdownまたはheading mapをPDFと再照合し、成功するまでvaultへ保存しない。

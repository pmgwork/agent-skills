# Referencesの入力と照合

`references.json` は次の配列。論文の `title` は正式な原題を使い、`number` はPDF中の引用番号を保持する。

```json
[
  {
    "number": 53,
    "kind": "paper",
    "title": "Tandem: Reproducible Digital Fabrication Workflows as Multimodal Programs",
    "doi": "10.1145/3613904.3642751",
    "year": 2024,
    "first_author": "Tran O’Leary"
  },
  {
    "number": 1,
    "kind": "artwork",
    "title": "Handshake",
    "url": "https://www.aatb.ch/archive/handshake"
  }
]
```

- 必須: 一意な正整数の `number`、`kind`、`title`。
- `kind`: 論文は `paper`。それ以外は `web`、`video`、`artwork`、`other` として元のHTTP(S) `url` を指定する。原本にURLがない書籍等は `citation` に原文の書誌情報を1行で入れ、通常のテキストとして保持する。URLを創作しない。
- 論文の `doi`、`year`、`first_author` は原本で確認できた場合のみ指定する。
- DOI一致を優先。見つからなければfrontmatterの `title`、先頭のH1、ファイル名を正規化して照合する。大文字小文字・空白・句読点の差を吸収するが、曖昧な部分一致はしない。
- 複数候補なら年・第一著者のメタデータを補助に使う。一意にならなければ停止する。内容を確認して選択できた既存ノートは `"target": "papers/実ファイル名"`（拡張子なし）で明示できる。古いノートのタイトル/DOIがメタデータにない場合もこの方法を使う。
- 未保存は共有の `sanitize_title()` で予定名を作る。別の文献が同じ保存名になる場合は停止する。自動で連番を付けず、正式タイトル・DOIの取り違えを確認する。区別が必要な命名変更は保存とリンク双方に反映する。
- 既存ノートのファイル名に `#`、`^`、`|` などのObsidianリンク用の区切りがある場合は停止して報告する。勝手にリネームしない。

Referencesは番号順に `53. [[papers/ノート名|原題]] ^ref-53` として出力する。原文の参考文献データは作業用JSONに残す。タイトルのみの一覧にしたくない依頼では著者・年・掲載先を保持する形式に合わせて処理を調整する。

本文の `[53]`、`[34, 50]`、`[3–7]` をブロックリンクに変換する。範囲は表記を保持し、両端の番号をリンクにする。範囲内も含め対応する文献がなければ停止する。Markdownのリンク、既存Wikilink、コード、数式、YAMLは引用番号として変換しない。

`link_references.py` の標準出力は各文献のリンク先、既存かどうか、本文で引用された番号のJSON。未保存リンクは正常な予定リンクとして報告し、リンク先の空ノートは作らない。References/IDを既に含む原稿は二重変換を避けるため受け付けない。

Obsidianの根拠: [Internal links](https://obsidian.md/help/links)。リストの個別項目は行末のブロックIDで参照でき、`[[#^ref-53|53]]` で同一ノートの該当項目へ移動する。Obsidian以外のMarkdown閲覧環境ではこの移動は保証しない。

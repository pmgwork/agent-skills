# Figure 1 抽出

Figure 1 / Fig. 1 / 図 1 が存在する場合は、Docling が出力した Markdown と `<PDF名>_artifacts/` の画像から Figure 1 を同定し、Obsidian ノートに埋め込めるように保存する。

保存先:

```text
papers/assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png
```

## 基本方針

`references/pdf_parsing.md` で 1 回だけ実行した Docling 変換の出力を使う。同じ PDF に対して Docling 変換を再実行しない。Figure 1 の同定は、専用スクリプトではなく、出力 Markdown の文脈を読んで行う。Figure 1 を十分に同定できない場合は、画像を作らない。

1. Docling が出力した Markdown を読み、`Figure 1` / `Fig. 1` / `図 1` の caption を探す。
2. その caption の直前（または直後）に並ぶ画像参照 `![...](<PDF名>_artifacts/xxx.png)` を Figure 1 候補として特定する。
3. caption と本文中の Figure 1 への言及を照合し、その画像が Figure 1 全体に対応することを確認する。
4. Figure 1 が複数の画像参照に分割されている場合は、本文の文脈から Figure 1 全体を構成する画像群を判断する。1 枚に収める必要がある場合は、Markdown 上の順序で結合してから保存する。
5. Figure 1 全体であると判断できる場合だけ、`papers/assets/{SanitizedTitle}/{SanitizedTitle}_figure1.png` としてコピー・保存する。
6. 候補が複数ある場合は、caption が `Figure 1` / `Fig. 1` / `図 1` に最も明確に対応するものを選ぶ。

## 抽出しない条件

次の場合は推測画像を作らない。frontmatter の `figure` と本文冒頭の画像埋め込みも作らず、完了報告で「Figure 1 は抽出できなかった」と明記する。

- Figure 1 caption に対応する画像参照が Markdown 上に見つからない。
- caption が欠落しており、Figure 1 との対応を確認できない。
- 書き出された画像が Figure 1 の一部だけである。
- 複数パネル図が分割され、Markdown 上の順序でも Figure 1 全体として構成できない。
- 表や本文ブロックが Figure 1 と誤判定されている可能性がある。

## 要約への反映

Figure 1 は論文内容の理解を補助する資料として扱う。画像内の文字や caption から読み取った内容を要約に反映する場合は、本文と照合して誤読を避ける。

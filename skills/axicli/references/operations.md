# AxiCLI 操作リファレンス

ローカルの `axicli --help` と [公式 CLI API](https://axidraw.com/doc/cli_api/) を最終的な仕様として扱う。

## モードと副作用

| 操作 | 入力 SVG | 実機への影響 | 判断 |
| --- | --- | --- | --- |
| `--version`, `version` | 不要 | なし | 実行可 |
| `--preview` | 必要 | なし | 実機操作の前に実行 |
| `sysinfo` | 不要 | 接続機を照会 | 必要時に実行可 |
| `manual` の `list_names`, `read_name`, `fw_version`, `res_read` | コマンドによる | 接続機を照会 | 必要時に実行可 |
| `plot`, `layers`, `res_plot`, `res_home` | 必要 | キャリッジ／ペンが動く | 明示依頼が必要 |
| `cycle`, `align`, `toggle` | 不要 | ペンまたはモーター状態が変わる | 明示依頼が必要 |
| その他の `manual` | コマンドによる | 移動、ペン、モーター、名前、bootloader 等を変更し得る | 個別の明示依頼が必要 |

## 定番コマンド

```sh
# ソフトウェア情報
axicli --version

# 接続情報（移動なし）
axicli --mode sysinfo
axicli --mode manual --manual_cmd list_names

# 全体をオフライン preview
axicli input.svg --preview --report_time --rendering 3 --output_file preview.svg

# 番号 5 で始まる top-level layer だけを preview
axicli input.svg --mode layers --layer 5 \
  --preview --report_time --rendering 3 --output_file layer-5-preview.svg

# 明示依頼後に全体を一度プロットし、停止時の progress を保存可能にする
axicli input.svg --mode plot --copies 1 --output_file plot-progress.svg

# 明示依頼後に番号 5 の layer だけを一度プロット
axicli input.svg --mode layers --layer 5 --copies 1 \
  --output_file layer-5-progress.svg
```

実際には必要な `--config`、`--model`、`--port`、pen height、速度、回転などを preview と実機コマンドの両方へ同じように付ける。短縮フラグより長いフラグを優先し、実行内容を読み返しやすくする。

## pause と resume

- 本体 Pause または `Ctrl+C` で停止する。現在の線分が終わってから止まる場合がある。
- resume には、停止時の位置と進捗が記録された `--output_file` の SVG が必要である。
- resume 時にも元の model、pen height、config などを再指定する。設定不一致は予期しない動作につながる。
- `res_home` で原点へ戻してから `res_plot` する場合は、`res_home` の結果を別の output SVG に保存し、その新しいファイルを次の入力に使う。
- どの resume 操作も自動実行しない。実機位置、入力 progress SVG、出力先、設定をユーザーと確認する。

## 複数台と危険度の高い指定

- 複数台では `list_names` で確認し、`--port` で一台を指定する。
- `--port_config 3` は全接続機へプロットするため、明示依頼なしに使わない。
- `--copies 0` は連続プロットである。回数が明示されない場合は `--copies 1` にする。
- `write_name` と `bootload` は通常の描画ワークフローに含めない。
- `--webhook_url` や設定ファイルの秘密情報をログ・回答へ転載しない。

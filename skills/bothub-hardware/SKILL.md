---
name: bothub-hardware
description: BotHub Hardware の Flask REST API を介して AxiDraw と GPIO 接続ソレノイドの状態確認、接続・切断、絶対座標移動、原点移動、パルス、GPIO 設定変更、解放を安全に行う。BotHub、bothub-hardware、AxiDraw REST API、/axiDraw、/solenoid、GPIO ソレノイド、座標移動、パルス動作に関する依頼で使う。
---

# BotHub Hardware

BotHub Hardware の REST API を安全に操作する。AxiDraw の移動とソレノイドの通電を物理的な副作用として扱う。

## 接続先と依存関係を確認する

標準クライアントは Python 標準ライブラリだけで動作する。

```sh
command -v python3
python3 scripts/bothub_hardware.py --help
```

接続先はユーザーの指定、`BOTHUB_HARDWARE_URL`、既定値 `http://localhost:8080` の順で決める。リモート URL を推測しない。API サーバーの起動や依存関係のインストールは、ユーザーが依頼した場合だけ行う。

別の作業ディレクトリから実行する場合は、`scripts/bothub_hardware.py` をこの Skill ディレクトリからの絶対パスに置き換える。

## 操作を分類する

- 読み取り: `info`、`status`、`solenoid-info`、`solenoid-status`
- AxiDraw の状態を変える: `connect`、`disconnect`、`move-default`、`move-to`
- GPIO／ソレノイドの状態を変える: `pulse`、`dispose`

読み取りはそのまま実行してよい。状態を変えるコマンドはユーザーが対象操作を明示的に依頼した場合だけ `--execute` を付ける。`--execute` がない場合、クライアントは送信予定を表示するだけで HTTP リクエストを送らない。

「状態を確認して」は接続、移動、パルスの許可ではない。失敗後に自動で再接続、再移動、再パルス、原点復帰を行わない。

## 状態を先に確認する

実機操作の前に API と接続状態を確認する。

```sh
python3 scripts/bothub_hardware.py info
python3 scripts/bothub_hardware.py status
python3 scripts/bothub_hardware.py solenoid-status
```

`available: false`、未接続、タイムアウト、接続拒否、非 2xx 応答があれば停止し、結果を報告する。AxiDraw の接続が必要なら、ユーザーの依頼範囲内で次を実行してから状態を再確認する。

```sh
python3 scripts/bothub_hardware.py connect --execute
```

## AxiDraw を移動する

`move-to` の単位は mm。現在状態が返す可動範囲に `x` と `y` が入ることを確認し、座標をユーザーに明示してから実行する。

```sh
python3 scripts/bothub_hardware.py move-to --x 50 --y 30 --execute
python3 scripts/bothub_hardware.py move-default --execute
```

`move-default` は物理移動であり、単なる状態リセットとして使わない。移動中に周囲、ケーブル、用紙、治具へ干渉する可能性がある場合は実行前にユーザーへ安全確認を求める。

## ソレノイドを動作させる

AxiDraw が接続済みであることを確認する。パルス時間を省略するとサーバー既定値の 0.5 秒になる。

```sh
python3 scripts/bothub_hardware.py pulse --execute
python3 scripts/bothub_hardware.py pulse --duration 1.0 --port C --pin 6 --default-state LOW --execute
```

GPIO を変更するときは `--port` と `--pin` を必ず同時に指定する。現在値と変更後の `port`、`pin`、`default_state`、パルス時間を実行前に短く提示する。配線仕様にない値を推測しない。連続パルスや反復実行は、回数と間隔をユーザーが明示した場合でも一回ずつ結果を確認し、異常応答があれば停止する。

GPIO を初期状態へ戻して解放する依頼には次を使う。

```sh
python3 scripts/bothub_hardware.py dispose --execute
```

## 結果を報告する

接続先、実行した操作、HTTP ステータス、API 応答の要点を報告する。移動後は可能なら `status`、パルスや解放後は `solenoid-status` で確認する。サーバーが返したエラー本文を保持し、成功を推測しない。

エンドポイントとリクエスト形式の詳細が必要な場合は [references/api.md](references/api.md) を読む。

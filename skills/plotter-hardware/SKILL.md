---
name: plotter-hardware
description: Plotter Hardware の Flask REST API と AxiDraw、B1イレーサー、B3ペン、D2ソレノイドを安全に扱う。サーバー状態確認、接続・切断、座標移動、ホーム、アクチュエータ操作、ソレノイド操作、単発描画、SVG描画ジョブ、ジョブ状態確認・キャンセルに関する依頼で使う。BotHub、plotter-hardware、Plotter Hardware、/axiDraw、/solenoid、/servo、/actuators、/drawing の依頼に対応する。
---

# Plotter Hardware

AxiDraw と多機構（ペン・イレーサー・ソレノイド）を制御する Plotter Hardware REST API サーバーと通信し、ハードウェアを安全に操作する。実機の移動、サーボ、GPIO ソレノイドは物理的な副作用として扱う。

## 接続とサーバー設定

- **接続先 URL**: 以下の優先順位で解決される。
  1. コマンドライン引数 `--base-url`
  2. 環境変数 `PLOTTER_HARDWARE_URL`（旧互換: `BOTHUB_HARDWARE_URL`）
  3. 既定値: `http://localhost:8080`
- **サーバーの起動（ローカルで起動する場合）**:
  サーバーのリポジトリルートで実行する（依存関係のインストールやサーバーの起動はユーザーが依頼した場合のみ行う）。
  ```sh
  # サーバー起動例（サーバーのリポジトリルートにて）
  python3 main.py --no-status
  # または
  make start
  ```
  起動後は `/docs`、`/openapi.json`、サーバーリポジトリの `README.md`、`openapi_spec.py` を API の正本として参照する。

- **補助クライアントスクリプト**:
  本スキル内の `scripts/plotter_hardware.py` を利用する。
  ```sh
  python3 scripts/plotter_hardware.py --help
  ```

## 操作を分類する

読み取り操作は次のエンドポイントを使う。

- `GET /axiDraw/`、`GET /axiDraw/status`
- `GET /solenoid/`、`GET /solenoid/status`
- `GET /servo/status`
- `GET /actuators/status`、`GET /actuators/config`
- `GET /drawing/`、`GET /drawing/status`
- `GET /drawing/jobs/{job_id}`、`GET /openapi.json`

接続、切断、ホーム、移動、サーボ、アクチュエータ、ソレノイド、単発描画、SVG描画ジョブの開始・キャンセルは状態を変える操作である。ユーザーが対象操作を明示的に依頼した場合だけ実行する。補助クライアントでは `--execute` がない限り POST を送信しない。

「状態を確認して」は接続、移動、パルス、サーボ、アクチュエータ操作、描画の許可ではない。失敗後に自動で再接続、再移動、再パルス、再描画、原点復帰を行わない。

## 実機操作の前に確認する

まず API が起動していることと、ハードウェアの利用可否・接続状態・描画ジョブの有無を確認する。

```sh
python3 scripts/plotter_hardware.py info
python3 scripts/plotter_hardware.py status
python3 scripts/plotter_hardware.py solenoid-status
python3 scripts/plotter_hardware.py servo-status
python3 scripts/plotter_hardware.py actuators-status
python3 scripts/plotter_hardware.py drawing-status
```

`available: false`、未接続、タイムアウト、接続拒否、非 2xx 応答があれば停止し、エラー本文を報告する。描画中は手動アクチュエータ操作と新しい描画を開始しない。API が `409` を返した場合は、ジョブ状態を確認してユーザーの指示を待つ。

接続操作が明示され、`GET /axiDraw/` が `available: true` の場合だけ次を実行する。

```sh
python3 scripts/plotter_hardware.py connect --execute
```

接続後は `status`、`solenoid-status`、`actuators-status` を再確認する。AxiDraw が利用不可なら接続を繰り返さない。

## AxiDraw の移動とホーム

`/axiDraw/move_to` と `/drawing/draw_to` の座標単位は mm。移動前に `/axiDraw/status` の `bounds` を読み、座標が範囲内にあることを確認する。実行前に対象座標をユーザーへ明示する。

```sh
python3 scripts/plotter_hardware.py move-to --x 50 --y 30 --execute
python3 scripts/plotter_hardware.py move-default --execute
```

`move-default` はソフトウェアが追跡する `(0, 0)` への移動であり、物理ホーミングではない。

`/axiDraw/home` は `walk_home` によるモーター原点復帰で、リミットスイッチを使わない。接続時にキャリッジを物理ホーム角へ置いておく必要があり、脱調・ベルト滑り・手動移動による実位置ずれを検出できない。ホーム操作は、周囲・用紙・治具・ケーブルとの干渉がないことをユーザーに確認してから実行する。実装上、ホーム前にソレノイドを OFF にする。

## 機構とソレノイド

機構名は `pen`（B3）、`eraser`（B1）、`solenoid`（D2）を使う。実際の GPIO とサーボ設定は `config/axidraw_conf.py` から読み込まれるため、ピンやオフセットを推測せず、必要なら先に `GET /actuators/config` で確認する。

```sh
python3 scripts/plotter_hardware.py actuator-down --tool pen --execute
python3 scripts/plotter_hardware.py actuator-up --tool pen --execute
python3 scripts/plotter_hardware.py pulse --duration 1.0 --execute
python3 scripts/plotter_hardware.py solenoid-toggle --execute
python3 scripts/plotter_hardware.py dispose --execute
```

GPIO を再設定するときは `port` と `pin` を必ず同時に指定する。`default_state` は `LOW` または `HIGH`。パルスの `duration` は正の秒数で、省略時はサーバー既定の 0.5 秒。連続パルスや反復操作は回数・間隔を明示し、1回ずつ結果を確認して異常応答で停止する。

`/servo/up`、`/servo/down`、`/servo/status` は互換用の B1 イレーサー操作である。新しい機構単位の操作には `/actuators/{pen|eraser|solenoid}/up|down` を使う。`/actuators/servo/...` は使わない。

## 単発描画と SVG ジョブ

`POST /drawing/draw_to` は、指定した機構を DOWN にして座標へ移動し、成功時も失敗時も UP に戻す。JSON の `x`、`y`、`pen` は必須。`pen` は `pen`、`eraser`、`solenoid`、旧互換の `servo`。`delay` は移動開始前の非負秒数で既定値は 0.5。`eraser_position_correction` は既定で有効で、`eraser`／`servo` のときだけ適用される。

```sh
python3 scripts/plotter_hardware.py draw-to --x 50 --y 30 --pen pen --delay 0.5 --execute
```

`POST /drawing/jobs` は UTF-8 の multipart フィールド `file` と必須の `pen` を受け取り、非同期に1件の SVG 描画を開始する。最大サイズは 10 MiB。DTD、entity、script、外部参照は拒否される。`options` は JSON オブジェクト文字列で、`layer`、`copies`、`speed_pendown`、`speed_penup`、`reordering`、`pen_down_delay`、`model`、`eraser_position_correction` を指定できる。サーバーは実行前に検証・見積もりを行い、`202` と `job_id` を返す。

ジョブ開始後は `GET /drawing/jobs/{job_id}` で `pending`、`running`、`cancelling`、`completed`、`failed`、`cancelled` を確認する。キャンセルはユーザーが明示した場合だけ `POST /drawing/jobs/{job_id}/cancel` を送る。描画失敗・キャンセル時も選択機構を安全状態へ戻すが、自動再実行・自動原点復帰は行わない。

## 結果を報告する

接続先、操作、対象座標または機構、HTTP ステータス、API 応答の要点を報告する。移動後は可能なら `status`、機構・ソレノイド操作後は `actuators-status` または `solenoid-status`、ジョブ開始後は `job_id` と最終状態を確認する。サーバーが返したエラー本文を保持し、成功を推測しない。

エンドポイントの詳細なリクエスト形式や制約が必要な場合は [references/api.md](references/api.md) を読み、実装と差異がある場合はプロジェクトの `openapi_spec.py` と現在のサーバーの `/openapi.json` を優先する。


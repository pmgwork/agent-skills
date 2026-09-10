---
name: plotter-hardware
description: AxiDraw または UUNA TEK DrawCore を選択する Plotter Hardware REST API を安全に操作する。状態確認、接続・切断、移動・ホーム、ペン等のアクチュエータ、単発描画、SVG 描画ジョブ、キャンセルの依頼で使う。
---

# Plotter Hardware

Plotter Hardware の共通 API `/plotter` を使う。サーバーは起動時に USB を検出し、UUNA TEK があれば `uuna_tek`、なければ `axidraw` を選ぶ。旧 `/axiDraw/*` は廃止済みなので使わない。

実機の移動、ホーム、接続・切断、アクチュエータ操作、描画開始・キャンセルは物理的な副作用を持つ。ユーザーが明示した操作だけを行い、失敗後の再接続、再移動、再描画、原点復帰を自動で行わない。

## クライアント

同梱の `scripts/plotter_hardware.py` を使う。接続先は `--base-url`、`PLOTTER_HARDWARE_URL`、`http://localhost:8080` の順で決まる。読み取りコマンドはそのまま送信し、POST コマンドは `--execute` がない限り dry-run になる。

```sh
python3 scripts/plotter_hardware.py --help
python3 scripts/plotter_hardware.py info
python3 scripts/plotter_hardware.py status
python3 scripts/plotter_hardware.py actuators-status
python3 scripts/plotter_hardware.py drawing-status
```

サーバーの起動や依存関係の導入は、ユーザーが依頼した場合だけ行う。API の現行仕様が必要なら、起動中の `GET /openapi.json`、サーバーリポジトリの `openapi_spec.py`、実装、テストを確認する。

## 操作前の判定

1. `info` で `available`、`connected`、`type`、`capabilities.tools` を確認する。
2. 接続済みなら `status` で現在位置と `bounds`、`drawing-status` または `actuators-status` で実行中ジョブを確認する。
3. `type` と `capabilities.tools` に合わない操作は送らない。

`available: false`、接続拒否、タイムアウト、非 2xx 応答では停止し、レスポンス本文を報告する。未接続時は、ユーザーが接続も依頼している場合だけ `connect --execute` を実行し、接続後に状態を再確認する。描画中または別操作中の POST は `409` になり得るため、状態を確認し、勝手に割り込みや再試行をしない。

## バックエンド別の制約

- `axidraw`: `pen`（B3）、`eraser`（B1）、`solenoid`（D2）を利用できる。`servo` は描画 API における `eraser` の旧別名である。`/servo/*` は AxiDraw 内蔵ペンリフトサーボ用の互換 API である。
- `uuna_tek`: 利用できる tool は `pen` のみ。`eraser`、`servo`、`solenoid` は HTTP 400 になる。ペン上下は DrawCore の Z 軸、XY 移動は共通 `/plotter/*`、SVG 描画は共通 `/drawing/jobs` を使う。

GPIO ピン、サーボ位置、イレーサー補正値、DOWN 待機時間を固定値で推測しない。AxiDraw では必要に応じて `actuators-config` を確認する。設定変更 API はない。

## 移動とホーム

座標は mm の絶対座標である。`move-to` と `draw-to` の前に `status.bounds` に入ることを確認する。AxiDraw のイレーサー補正を使う場合は、補正後の座標をサーバーが再検証するため、エラー時に補正を勝手に無効化しない。

```sh
python3 scripts/plotter_hardware.py move-to --x 50 --y 30
python3 scripts/plotter_hardware.py move-to --x 50 --y 30 --execute
```

`move-default` は追跡座標 `(0, 0)` への移動であり、物理ホーミングではない。`home` の意味はバックエンドで異なる。

- AxiDraw: `walk_home` でモーター有効化時の位置へ戻る。リミットスイッチは使わず、脱調、ベルト滑り、手動移動によるずれを検出できない。
- UUNA TEK: DrawCore の `$H` を実行する。リミットスイッチ構成は API 側で検証されず、`uses_limit_switch` は `null` である。

どちらも移動経路と周囲の安全、機械側のホーム条件をユーザーに確認してから実行する。返却された `homing_method` と `uses_limit_switch` を報告する。

## アクチュエータと描画

手動操作は `/actuators/{pen|eraser|solenoid}/up|down` を優先する。論理上、`up` はペン・イレーサーを離隔しソレノイドを OFF、`down` は接触させソレノイドを ON にする。反復操作は回数を明示し、1 回ごとに状態を確認する。

`draw-to` は範囲検証後に tool を DOWN、指定時間待機、移動、UP の順で処理し、移動失敗時も UP を試みる。AxiDraw の `eraser`／`servo` は位置補正が既定で有効である。ユーザーの意図なく `--no-eraser-position-correction` を付けない。

SVG は UTF-8、最大 10 MiB。`plot-svg` は開始前にローカルファイルと `options` JSON を検証し、サーバーは SVG の安全性検査と見積もりを行う。UUNA TEK では必ず `--pen pen` を使う。

```sh
python3 scripts/plotter_hardware.py draw-to --x 50 --y 30 --pen pen --delay 0.5
python3 scripts/plotter_hardware.py plot-svg --file drawing.svg --pen pen --options '{"copies":1}'
```

dry-run の内容を確認してから、同じコマンドに `--execute` を付ける。SVG 開始後は返却された `job_id` を保存し、`plot-status` で `completed`、`failed`、`cancelled` のいずれかまで確認する。キャンセルはユーザーが明示した場合だけ実行する。

詳細なエンドポイントと入力形式は [references/api.md](references/api.md) を参照する。

## 報告

接続先、選択された `type`、実行した操作、座標または tool、HTTP ステータス、応答の要点を報告する。操作後は対応する状態 API を再確認し、エラー本文を保持する。成功を推測しない。

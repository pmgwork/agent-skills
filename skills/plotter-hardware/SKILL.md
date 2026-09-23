---
name: plotter-hardware
description: 互換パス /axiDraw を使う Plotter Hardware REST API を安全に操作する。AxiDraw または UUNA TEK DrawCore と M5StickC イレーサーの状態確認、接続・切断、移動・ホーム、アクチュエータ、単発描画、SVG 描画ジョブ、キャンセルの依頼で使う。
---

# Plotter Hardware

現行 API は、選択された AxiDraw または UUNA TEK DrawCore を互換パス `/axiDraw/*` から操作する。`/plotter/*` はこの版には存在しない。サーバーは起動時に USB を検出し、UUNA TEK があれば `uuna_tek`、なければ `axidraw` を内部で選ぶ。UUNA TEK のイレーサーは別ネットワーク上の M5StickC を介して動作し、設定で無効化できる。

実機の移動、ホーム、接続・切断、アクチュエータ操作、描画開始・キャンセルは物理的な副作用を持つ。ユーザーが明示した操作だけを行い、失敗後の再接続、再移動、再描画、原点復帰を自動で行わない。

## クライアント

同梱の `scripts/plotter_hardware.py` を使う。接続先は `--base-url`、`PLOTTER_HARDWARE_URL`、`http://localhost:8080` の順で決まる。GET はそのまま送信し、POST は `--execute` がない限り dry-run になる。

```sh
python3 scripts/plotter_hardware.py --help
python3 scripts/plotter_hardware.py info
python3 scripts/plotter_hardware.py status
python3 scripts/plotter_hardware.py actuators-config
python3 scripts/plotter_hardware.py actuators-status
python3 scripts/plotter_hardware.py drawing-status
```

サーバーの起動や依存関係の導入は、ユーザーが依頼した場合だけ行う。API の現行仕様が必要なら、起動中の `GET /openapi.json`、サーバーリポジトリの `openapi_spec.py`、`api_server.py`、テストを確認する。

## 操作前の判定

1. `info` で `available` と `connected` を確認する。
2. `actuators-config` でバックエンドと実装済み機構を判定する。`driver: uuna_tek` なら UUNA TEK で、`pen.implemented`、`eraser.implemented`、`solenoid.implemented` を個別に確認する。`servo_profiles` と `solenoid_*` を持つ設定なら AxiDraw である。現行の `info` は `type` や `capabilities` を返さない。
3. 接続済みなら `status` で現在位置と `bounds`、`drawing-status` で `active_job`、`actuators-status` で機構状態を確認する。
4. 設定からバックエンドを判定できない場合、バックエンド固有の機構を操作しない。

`available: false`、接続が必要な操作での `connected: false`、`success: false`、レスポンス内の `error`、タイムアウト、非 2xx 応答では停止し、レスポンス本文を報告する。切断成功後の `connected: false` は正常である。接続・切断失敗でも現行実装は HTTP 200 を返し得るため、HTTP ステータスだけで成功判定しない。未接続時は、ユーザーが接続も依頼している場合だけ `connect --execute` を実行し、接続後に状態を再確認する。

描画中のアクチュエータ操作やホームは `409` になり得る。現行実装では単純移動などすべての競合を一律には拒否しないため、POST 前に `active_job` を確認し、ジョブ中はキャンセルを含めユーザーが明示した操作以外を送らない。

## バックエンド別の制約

- `axidraw`: `pen`（B3）、`eraser`（B1）、`solenoid`（D2）を利用できる。描画 API の `servo` は `eraser` の旧別名である。`/servo/*` は AxiDraw 内蔵ペンリフトサーボ用の互換 API である。
- `uuna_tek`: `pen` は DrawCore の Z 軸を動かす。`eraser.implemented: true` のときだけ、`eraser` と旧別名 `servo` が M5StickC 経由の L12-R を動かす。`eraser.implemented: false` と `solenoid.implemented: false` は互換用の無動作なので送らない。`/actuators/status`、`/servo/status`、`/solenoid/status` の `available` だけで実機対応を判断せず、`actuators-config` の `implemented` を優先する。

GPIO ピン、サーボ位置、イレーサー補正値、DOWN 待機時間、M5StickC の接続先を固定値で推測しない。どちらのバックエンドでも `actuators-config` を確認する。設定変更 API はない。

## 移動とホーム

座標は mm の絶対座標である。`move-to` と `draw-to` の前に、補正後の座標も含め `status.bounds` に入ることを確認する。AxiDraw のイレーサー補正でエラーになっても、補正を勝手に無効化しない。

```sh
python3 scripts/plotter_hardware.py move-to --x 50 --y 30
python3 scripts/plotter_hardware.py move-to --x 50 --y 30 --execute
```

`move-default` は追跡座標 `(0, 0)` への移動であり、物理ホーミングではない。`home` の実処理はバックエンドで異なる。

- AxiDraw: `walk_home` でモーター有効化時の位置へ戻る。リミットスイッチは使わず、脱調、ベルト滑り、手動移動によるずれを検出できない。
- UUNA TEK: DrawCore の `$H` を実行後、論理原点を再設定する。

どちらも移動経路と周囲の安全、機械側のホーム条件をユーザーに確認してから実行する。現行 `/axiDraw/home` の応答は UUNA TEK にも `homing_method: walk_home`、`uses_limit_switch: false` を返す実装上の不整合があるため、UUNA TEK ではこのメタデータを実処理の証拠として扱わない。

## アクチュエータと描画

手動操作は `/actuators/{pen|eraser|solenoid}/up|down` を使う。論理上、`up` はペン・イレーサーを離隔しソレノイドを OFF、`down` は接触させソレノイドを ON にする。反復操作は回数を明示し、1 回ごとに状態を確認する。

`draw-to` は範囲検証後に tool を DOWN、指定時間待機、移動、UP の順で処理し、移動失敗時も UP を試みる。AxiDraw と UUNA TEK の `eraser`／`servo` は位置補正が既定で有効である。ユーザーの意図なく `--no-eraser-position-correction` を付けない。

SVG は UTF-8、最大 10 MiB。`plot-svg` は送信時にローカルファイルと `options` JSON を検証し、サーバーは SVG の安全性検査と見積もりを行う。UUNA TEK では `pen`、または `eraser.implemented: true` を確認したうえで `eraser` を使う。機械範囲から完全に外れて描画可能パスが残らない SVG は開始前に拒否され、一部がクリップされる場合は `preview.warnings` を確認する。

```sh
python3 scripts/plotter_hardware.py draw-to --x 50 --y 30 --pen pen --delay 0.5
python3 scripts/plotter_hardware.py plot-svg --file drawing.svg --pen pen --options '{"copies":1}'
```

dry-run の内容を確認してから、同じコマンドに `--execute` を付ける。SVG 開始後は返却された `job_id` を保存し、`plot-status` で `completed`、`failed`、`cancelled` のいずれかまで確認する。キャンセルはユーザーが明示した場合だけ実行する。

詳細なエンドポイントと入力形式は [references/api.md](references/api.md) を参照する。

## 報告

接続先、`actuators-config` から判定したバックエンドと実装済み tool、実行した操作、座標または tool、HTTP ステータス、`success`／`error`、SVG の警告を報告する。操作後は対応する状態 API を再確認する。互換用の無動作を実機成功として報告せず、成功を推測しない。

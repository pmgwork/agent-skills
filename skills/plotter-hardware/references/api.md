# Plotter Hardware API reference

対象実装: `/Users/yuto/Documents/GitHub/laboratory/plotter-hardware`。既定 URL は `http://localhost:8080`。最終的なレスポンスフィールド、制約、HTTP ステータスはプロジェクトの `openapi_spec.py` または起動中の `GET /openapi.json` を優先する。

## AxiDraw API

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/axiDraw/` | — | サービス情報、`available`、`connected` |
| `POST` | `/axiDraw/connect` | `{}` | AxiDraw と GPIO 機構を初期化して接続 |
| `POST` | `/axiDraw/disconnect` | `{}` | 機構を安全状態にして切断 |
| `GET` | `/axiDraw/status` | — | 接続状態、現在位置、可動範囲 |
| `POST` | `/axiDraw/move_to_default` | `{}` | ソフトウェア原点 `(0, 0)` へ移動 |
| `POST` | `/axiDraw/home` | `{}` | `walk_home` でモーター原点へ戻し、座標を再同期 |
| `POST` | `/axiDraw/move_to` | `{"x": 50.0, "y": 30.0}` | 絶対座標へ移動（mm） |

`/axiDraw/home` はリミットスイッチを使わない。`move_to_default` は物理ホーミングではない。`move_to` 実行前に `status.bounds` を確認する。

## Solenoid API

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/solenoid/` | — | 初期化状態、ポート、ピン、既定状態、論理状態 |
| `GET` | `/solenoid/status` | — | `available`、`ready`、接続、GPIO、状態 |
| `POST` | `/solenoid/toggle` | `{}` または下記 | 現在状態を反転 |
| `POST` | `/solenoid/pulse` | `{}` または下記 | 1回パルス |
| `POST` | `/solenoid/dispose` | `{}` | GPIO を既定状態へ戻して解放 |

再設定を伴う body の例:

```json
{
  "duration": 1.0,
  "port": "D",
  "pin": "2",
  "default_state": "LOW"
}
```

- `duration` は正の秒数。省略時は 0.5 秒。
- `port` または `pin` を指定して再設定する場合は両方が必須。
- `default_state` は `LOW` または `HIGH`。
- `toggle` は `previous_state`、`state`、現在の GPIO 設定を返す。
- AxiDraw 未接続時の `toggle`／`pulse` は実行できない。

## Servo API

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `POST` | `/servo/up` | `{}` | 互換用 B1 イレーサーを UP |
| `POST` | `/servo/down` | `{}` | 互換用 B1 イレーサーを DOWN |
| `GET` | `/servo/status` | — | 互換用サーボ状態 |

機構を明示する新しい API は `/actuators/pen`、`/actuators/eraser`、`/actuators/solenoid` を使う。

## Actuators API

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/actuators/status` | — | B3 `pen`、B1 `eraser`、D2 `solenoid` の状態とジョブ状態 |
| `GET` | `/actuators/config` | — | `config/axidraw_conf.py` の検証済み設定 |
| `POST` | `/actuators/{tool}/up` | `{}` | `pen`／`eraser` を離隔、または solenoid を OFF |
| `POST` | `/actuators/{tool}/down` | `{}` | `pen`／`eraser` を動作、または solenoid を ON |

`tool` は `pen`、`eraser`、`solenoid` のいずれか。`servo` はこのパスの有効値ではない。GPIO やサーボピンは設定 API で確認し、固定値を推測しない。

## Drawing API

### 単発移動

`POST /drawing/draw_to` は JSON を受け取る。

```json
{
  "x": 50.0,
  "y": 30.0,
  "pen": "eraser",
  "delay": 0.5,
  "eraser_position_correction": true
}
```

- `x`、`y`、`pen` は必須。座標は mm。
- `pen` は `pen`、`eraser`、`solenoid`、互換値 `servo`。
- `delay` は非負秒数で既定値は 0.5。
- `eraser_position_correction` は boolean、既定値は `true`。`eraser`／`servo` のみ補正。
- 旧 `margin` パラメータは拒否される。
- 移動失敗時も選択した機構を UP／OFF に戻す。

### SVG ジョブ

`POST /drawing/jobs` は multipart/form-data を受け取る。

- `file`: UTF-8 SVG ファイル（必須、最大 10 MiB）
- `pen`: `pen`、`eraser`、`solenoid`、`servo`（必須）
- `options`: JSON オブジェクト文字列（任意）

`options` の対応キー:

```json
{
  "layer": 0,
  "copies": 1,
  "speed_pendown": 25,
  "speed_penup": 50,
  "reordering": 0,
  "pen_down_delay": 0.5,
  "model": 4,
  "eraser_position_correction": true
}
```

SVG の DTD、entity、script、外部参照は拒否される。実行前に内部検証・見積もりを行い、成功時は `202` と `job_id`、`preview`、`metadata`、`options` を返す。描画中の新規ジョブは `409`。

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/drawing/` または `/drawing/status` | 描画層、各 pen の状態、active job |
| `POST` | `/drawing/jobs` | 非同期 SVG 描画を開始 |
| `GET` | `/drawing/jobs/{job_id}` | ジョブ状態、結果、エラー |
| `POST` | `/drawing/jobs/{job_id}/cancel` | 実行中ジョブをキャンセル |

ジョブ状態の終端値は `completed`、`failed`、`cancelled`。開始後は `job_id` を保存し、状態を再取得する。キャンセル済み・完了済みジョブへのキャンセルは `409`。

## 起動と確認

```sh
cd /Users/yuto/Documents/GitHub/laboratory/plotter-hardware
./.venv/bin/python main.py --no-status
curl http://localhost:8080/axiDraw/
curl http://localhost:8080/axiDraw/status
curl http://localhost:8080/actuators/config
curl http://localhost:8080/openapi.json
```

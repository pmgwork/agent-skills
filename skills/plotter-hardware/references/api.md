# Plotter Hardware API reference

既定 URL は `http://localhost:8080`。現行 API は AxiDraw と UUNA TEK DrawCore に共通の `/plotter` を使う。旧 `/axiDraw/*` は 404 になる。

## Plotter API

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/plotter/` | — | `available`、`connected`、`type`、`capabilities.tools` |
| `POST` | `/plotter/connect` | `{}` | 起動時に選択されたプロッタへ接続 |
| `POST` | `/plotter/disconnect` | `{}` | 安全状態にして切断 |
| `GET` | `/plotter/status` | — | 現在位置と可動範囲 |
| `POST` | `/plotter/move_to_default` | `{}` | 追跡座標 `(0, 0)` へ移動 |
| `POST` | `/plotter/home` | `{}` | バックエンド固有のホームを実行し座標を再同期 |
| `POST` | `/plotter/move_to` | `{"x": 50.0, "y": 30.0}` | 絶対座標へ移動（mm） |

`type` は `axidraw` または `uuna_tek`。UUNA TEK はサーバー起動時の USB 検出で優先選択され、API 操作だけでは別バックエンドへ切り替えられない。

`home` の応答には `homing_method` と `uses_limit_switch` が含まれる。AxiDraw は `walk_home`／`false`、UUNA TEK は `$H`／`null`。`move_to_default` は物理ホーミングではない。

## Actuators and compatibility APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/actuators/status` | 対応機構、状態、busy、active job |
| `GET` | `/actuators/config` | ファイル由来の機構設定 |
| `POST` | `/actuators/{tool}/up` | 離隔または OFF |
| `POST` | `/actuators/{tool}/down` | 接触または ON |
| `GET` | `/servo/status` | AxiDraw 内蔵サーボ状態 |
| `POST` | `/servo/up`, `/servo/down` | AxiDraw 内蔵サーボ操作 |

`tool` は `pen`、`eraser`、`solenoid`。AxiDraw では順に B3、B1、D2。UUNA TEK では `pen` だけが利用でき、他の機構と `/servo` の POST は 400、状態取得は `available: false` になる。

## Solenoid API

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/solenoid/`, `/solenoid/status` | — | 利用可否、接続、GPIO、状態 |
| `POST` | `/solenoid/toggle` | `{}` または GPIO 設定 | 現在状態を反転 |
| `POST` | `/solenoid/pulse` | `{}` または下記 | 1 回パルス |
| `POST` | `/solenoid/dispose` | `{}` | 既定状態へ戻して解放 |

```json
{
  "duration": 1.0,
  "port": "D",
  "pin": "2",
  "default_state": "LOW"
}
```

`duration` は正の秒数で、省略時は 0.5 秒。再設定では `port` と `pin` を同時に指定する。`default_state` は `LOW` または `HIGH`。この API は AxiDraw 専用である。

## Drawing API

`POST /drawing/draw_to`:

```json
{
  "x": 50.0,
  "y": 30.0,
  "pen": "pen",
  "delay": 0.5,
  "eraser_position_correction": true
}
```

- `x`、`y`、`pen` は必須。`pen` は `pen`、`eraser`、`solenoid`、旧別名 `servo`。
- `delay` は機構固有の DOWN 待機に加える非負秒数。既定値は 0.5。
- `eraser_position_correction` は既定で `true`。AxiDraw の `eraser`／`servo` のみに適用される。
- 旧 `margin` は拒否される。
- 事前に座標を検証し、成功・失敗のどちらでも選択機構を UP／OFF に戻す。

SVG ジョブ:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/drawing/`, `/drawing/status` | 描画層、各 tool、active job |
| `POST` | `/drawing/jobs` | multipart で非同期 SVG 描画を開始 |
| `GET` | `/drawing/jobs/{job_id}` | ジョブ状態を取得 |
| `POST` | `/drawing/jobs/{job_id}/cancel` | 実行中ジョブをキャンセル |

`POST /drawing/jobs` の multipart フィールド:

- `file`: UTF-8 SVG、必須、最大 10 MiB。
- `pen`: 必須。UUNA TEK は `pen` のみ。
- `options`: 任意の JSON オブジェクト文字列。対応キーは `layer`、`copies`、`speed_pendown`、`speed_penup`、`reordering`、`pen_down_delay`、`model`、`eraser_position_correction`。

DTD、entity、script、外部参照は拒否される。成功時は 202 と `job_id`、`preview`、`metadata`、`options` が返る。ジョブ状態は `pending`、`running`、`cancelling`、`completed`、`failed`、`cancelled`。同時操作は 409 になり得る。

## 代表的なエラー境界

- 未対応 tool や未接続など、要求を実行できない場合: 400。
- 描画中・別操作中、既に終端状態のジョブをキャンセルする場合: 409。
- 接続・切断に失敗した場合: 503。
- ハードウェア実行中の例外: 500。

レスポンス本文の `error` を確認する。OpenAPI と実装が食い違う場合は、起動中のレスポンスとサーバー実装・テストを優先する。

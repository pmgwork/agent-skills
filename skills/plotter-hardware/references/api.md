# Plotter Hardware API reference

既定 URL は `http://localhost:8080`。現行 API は AxiDraw と UUNA TEK DrawCore に共通の互換パス `/axiDraw` を使う。`/plotter/*` は 404 になる。

## Plotter API

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/axiDraw/` | — | `available`、`connected`、サービス状態 |
| `POST` | `/axiDraw/connect` | `{}` | 起動時に選択されたプロッタへ接続 |
| `POST` | `/axiDraw/disconnect` | `{}` | 安全状態にして切断 |
| `GET` | `/axiDraw/status` | — | 現在位置と可動範囲 |
| `POST` | `/axiDraw/move_to_default` | `{}` | 追跡座標 `(0, 0)` へ移動 |
| `POST` | `/axiDraw/home` | `{}` | バックエンド固有のホームを実行し座標を再同期 |
| `POST` | `/axiDraw/move_to` | `{"x": 50.0, "y": 30.0}` | 絶対座標へ移動（mm） |

サーバー起動時に UUNA TEK USB（VID/PID `1a86:7523` または `1a86:8040`）を検出すると UUNA TEK を優先し、なければ AxiDraw を選ぶ。API 操作だけでは切り替えられない。`GET /axiDraw/` は選択された type や capabilities を公開しないため、`GET /actuators/config` の形で判定する。

- UUNA TEK: `driver` が `uuna_tek`。`pen.implemented` は `true`、`eraser.implemented` と `solenoid.implemented` は `false`。
- AxiDraw: `servo_profiles`、`solenoid_port`、`solenoid_pin` を持つ。

接続・切断は失敗時も HTTP 200 で `success: false` と `error` を返し得る。未接続の `status` も HTTP 200 で `connected: false` と `error` を返す。

`move_to_default` は物理ホーミングではない。AxiDraw の `home` は `walk_home`、UUNA TEK の `home` は `$H` を実行する。ただし現行レスポンスはバックエンドを問わず `homing_method: walk_home`、`uses_limit_switch: false` とするため、UUNA TEK ではこの2フィールドが実処理と一致しない。

## Actuators and compatibility APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/actuators/status` | 対応機構、状態、busy、active job |
| `GET` | `/actuators/config` | バックエンドの機構設定 |
| `POST` | `/actuators/{tool}/up` | 離隔または OFF |
| `POST` | `/actuators/{tool}/down` | 接触または ON |
| `GET` | `/servo/status` | AxiDraw 内蔵サーボ互換状態 |
| `POST` | `/servo/up`, `/servo/down` | AxiDraw 内蔵サーボ操作 |

`tool` は `pen`、`eraser`、`solenoid`。AxiDraw では順に B3、B1、D2。UUNA TEK で実装されるのは `pen` だけである。ただし現行実装は未実装 tool を 400 にせず無動作で成功させ、status の `available` を真にする場合がある。物理対応の判断には `/actuators/config` の `implemented` を使う。

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

`duration` は正の秒数で、省略時は 0.5 秒。再設定では `port` と `pin` を同時に指定する。`default_state` は `LOW` または `HIGH`。実機操作は AxiDraw 専用であり、UUNA TEK の互換ソレノイドは無動作である。

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
- UUNA TEK で物理描画するには `pen` を指定する。他の値は無動作になり得る。

SVG ジョブ:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/drawing/`, `/drawing/status` | 描画層、各 tool、active job |
| `POST` | `/drawing/jobs` | multipart で非同期 SVG 描画を開始 |
| `GET` | `/drawing/jobs/{job_id}` | ジョブ状態を取得 |
| `POST` | `/drawing/jobs/{job_id}/cancel` | 実行中ジョブをキャンセル |

`POST /drawing/jobs` の multipart フィールド:

- `file`: UTF-8 SVG、必須、最大 10 MiB。
- `pen`: 必須。UUNA TEK で実機描画する場合は `pen` のみ。
- `options`: 任意の JSON オブジェクト文字列。対応キーは `layer`、`copies`、`speed_pendown`、`speed_penup`、`reordering`、`pen_down_delay`、`model`、`eraser_position_correction`。同名の個別 multipart フィールドでも指定でき、個別値が JSON を上書きする。

DTD、entity、script、外部参照は拒否される。成功時は 202 と `job_id`、`preview`、`metadata`、`options` が返る。ジョブ状態は `pending`、`running`、`cancelling`、`completed`、`failed`、`cancelled`。同時ジョブや一部の同時操作は 409 になり得る。

## 代表的なエラー境界

- 未接続、不正入力、未利用ハードウェア: 400。ただし UUNA TEK の未実装 tool は互換用無動作として成功する場合がある。
- 描画中の一部操作、既に終端状態のジョブのキャンセル、状態不明の solenoid toggle: 409。
- home 実装がない場合: 501。
- ハードウェア実行中の例外: 500。
- 存在しないジョブ: 404。

HTTP 2xx だけでなく、レスポンス本文の `success`、`connected`、`error` を確認する。OpenAPI と実装が食い違う場合は、起動中のレスポンスとサーバー実装・テストを優先する。

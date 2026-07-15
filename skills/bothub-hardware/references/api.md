# BotHub Hardware API reference

既定のベース URL は `http://localhost:8080`。座標は mm 単位。

## AxiDraw

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/axiDraw/` | — | API 情報と `available` |
| `POST` | `/axiDraw/connect` | `{}` | AxiDraw に接続 |
| `POST` | `/axiDraw/disconnect` | `{}` | AxiDraw から切断 |
| `GET` | `/axiDraw/status` | — | 接続状態、現在位置、可動範囲 |
| `POST` | `/axiDraw/move_to_default` | `{}` | 原点へ移動 |
| `POST` | `/axiDraw/move_to` | `{"x": 50.0, "y": 30.0}` | 絶対座標へ移動 |

## Solenoid

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/solenoid/` | — | API 情報、初期化状態、GPIO 設定 |
| `GET` | `/solenoid/status` | — | 利用可否、接続状態、GPIO 設定 |
| `POST` | `/solenoid/pulse` | `{}` または下記 | 一回パルス動作 |
| `POST` | `/solenoid/dispose` | `{}` | GPIO を初期状態に戻して解放 |

`pulse` の全指定例:

```json
{
  "duration": 1.0,
  "port": "C",
  "pin": "6",
  "default_state": "LOW"
}
```

- `duration` の省略時は 0.5 秒。
- GPIO 再設定は `port` と `pin` を同時に指定した場合だけ行われる。
- AxiDraw 未接続時の `pulse` は HTTP 400。
- AxiDraw を初期化できない場合、`GET /axiDraw/` は `available: false`。

具体的なレスポンスフィールドや制約は、対象サーバーに同梱された `docs/api_swagger.yaml` を最優先する。この参照にない値や挙動を推測しない。

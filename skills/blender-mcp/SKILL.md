---
name: blender-mcp
description: Control Blender through the configured Blender MCP server. Use when the user asks to inspect, create, edit, organize, troubleshoot, preview, render, or verify a Blender scene, object, material, modifier, collection, camera, or .blend file. Covers live Blender sessions and explicit background processing of a supplied .blend file, with inspect-first, minimal-mutation, and read-back verification workflows.
---

# Blender MCP

接続中の Blender のシーンや、ユーザーが明示した `.blend` ファイルを確認・編集・検証する。`bpy` の一般的な注意（オペレーターとデータ API の使い分け、active と選択、`bmesh`、依存グラフの更新、同梱ドキュメントの検索）は MCP サーバーの説明に従い、ここではそれ以外の手順と注意だけを扱う。

## 経路と安全

- ライブ操作は `execute_blender_code`、ユーザーが `.blend` を明示した場合のバックグラウンド処理は `execute_blender_code_for_cli` を使う。接続できない場合は報告して止め、別のファイルやプロセスを推測して操作しない。
- 保存、上書き、外部ファイル（ライブラリ・テクスチャ・キャッシュ）の置換、広範囲の削除は、依頼に含まれる場合だけ行う。保存時は出力パスを確認し、保存先を報告する。
- 対象が複数解釈できる場合は、破壊的な操作を推測で始めない。

## 検査

シーン全体をいきなりダンプせず、必要な範囲だけ段階的に取得する。

1. `get_blendfile_summary_path_info`（パス・保存状態）、`get_blendfile_summary_datablocks`（データブロック数・レンダーエンジン）
2. `get_objects_summary`（コレクション階層・オブジェクト一覧）
3. 対象が決まったら `get_object_detail_summary({ name })`
4. 外部参照が関係するときは `get_blendfile_summary_missing_files`、`get_blendfile_summary_of_linked_libraries`

見た目の依頼では `get_screenshot_of_window_as_json` で画面状態を確認し、スクリーンショット系ツールで実際の表示を見る。隠し状態を変える `allow_edits: true` は依頼に含まれる場合だけ使う。

## 編集

- 名前衝突で `.001` などが付くため、作成直後の参照を保持し、推測した名前で探し直さない。
- 共有データブロックの `users` を確認する。共有メッシュやマテリアルの変更は複数オブジェクトに及ぶため、必要なら single-user 化してから変更する。
- 直接のメッシュ確定編集より、モディファイアなど非破壊的な手段を優先する。
- 回転は `rotation_mode` を確認して正しいプロパティへ書く。親付きオブジェクトの `location` をワールド位置とみなさず、`matrix_world` から読む。
- 非均一スケールのままブーリアンや物理計算をしない。スケール適用が破壊的にならないか確認する。
- コードは短く検査可能にし、`print` ではなく JSON 化できる値を `result` に代入して返す。途中で失敗し得る大きな一括処理や、対象不明の全削除は避ける。

```python
import bpy

obj = bpy.data.objects.get("Target")
result = {"ok": False, "reason": "object_not_found"} if obj is None else {
    "ok": True, "name": obj.name, "location": list(obj.location),
    "rotation_mode": obj.rotation_mode, "users": getattr(obj.data, "users", None),
}
```

## 読み戻し

変更後は `get_object_detail_summary` か `get_objects_summary` で期待値を確認する。見た目が重要な場合はスクリーンショットか `render_thumbnail_to_path`／`render_viewport_to_path` で確認し、メタデータだけで見た目を断定しない。

## トラブルシューティング

- タイムアウト後は同じ編集を再実行せず、まず状態を読んで反映済みか確認する。
- オペレーターが失敗したら、モード・active・選択・可視性・コレクション除外を確認してから直す。
- オブジェクトが見えないときは、ビューポート非表示、View Layer での除外、レンダー無効を区別する。

## 報告

対象、実行内容と読み戻し結果、画像・保存ファイルの絶対パス、保存の有無（読み取り専用なら「シーンの変更は行っていない」）、未確認事項を日本語で簡潔に報告する。

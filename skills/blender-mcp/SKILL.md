---
name: blender-mcp
description: Control Blender through the configured Blender MCP server. Use when the user asks to inspect, create, edit, organize, troubleshoot, preview, render, or verify a Blender scene, object, material, modifier, collection, camera, or .blend file. Covers live Blender sessions and explicit background processing of a supplied .blend file, with inspect-first, minimal-mutation, and read-back verification workflows.
---

# Blender MCP

Blender MCP を通じて、現在接続されている Blender のシーンや、ユーザーが明示した `.blend` ファイルを確認・編集・検証する。シーンの状態を推測せず、対象を特定してから最小限の変更を行い、最後に構造または画像で結果を読み戻す。

## 前提と経路の選択

- ライブ操作では、Blender が起動し、MCP アドオンが接続されていることを確認する。接続できない場合は、接続不備を報告して止める。
- `mcp__blender__execute_blender_code` は接続中の Blender に `bpy` コードを実行する。通常の操作を行う専用 MCP ツールがある場合はそちらを優先し、専用操作がない編集だけに使う。
- `mcp__blender__execute_blender_code_for_cli` は、ユーザーが対象の `.blend` ファイルを明示した場合のバックグラウンド処理に使う。ファイルパスを推測したり、ライブ接続の代わりに勝手に別ファイルを開いたりしない。
- ファイルの保存、上書き、外部ファイルの置換、広範囲の削除は状態を変える操作である。依頼に含まれない限り実行しない。保存した場合は、保存先と保存状態を必ず報告する。

## 標準ワークフロー

### 1. 依頼の境界を決める

最初に、対象（シーン、コレクション、オブジェクト名、データブロック名、または `.blend` パス）、変更内容、出力（スクリーンショット、レンダー、保存ファイルなど）、読み取り専用か編集かを整理する。対象が複数解釈できる場合は、破壊的な操作を推測で始めない。

### 2. シーンを段階的に検査する

大きなシーン全体や全メッシュをいきなりダンプせず、次の順で必要な情報だけ取得する。

1. `mcp__blender__get_blendfile_summary_path_info` でファイルパス、保存状態、バックアップ情報を確認する。
2. `mcp__blender__get_blendfile_summary_datablocks` でデータブロック数、アクティブワークスペース、レンダーエンジンを確認する。
3. `mcp__blender__get_objects_summary` でコレクション階層、オブジェクト名・種別・親子関係・選択・可視性を確認する。
4. 対象が決まったら `mcp__blender__get_object_detail_summary({ name })` でトランスフォーム、親子、モディファイア、制約、マテリアル、データブロック、コレクションを確認する。
5. 必要に応じて `mcp__blender__get_blendfile_summary_missing_files` と `mcp__blender__get_blendfile_summary_of_linked_libraries` で外部参照を確認する。

視覚的な依頼では、`mcp__blender__get_screenshot_of_window_as_json` でウィンドウ状態・エリア・アクティブオブジェクト・選択を確認し、`mcp__blender__get_screenshot_of_window_as_image` または `mcp__blender__get_screenshot_of_area_as_image` で実際の表示を確認する。必要なら `mcp__blender__jump_to_view3d_object_by_name` で対象をフレームするが、可視化のために隠し状態を変える `allow_edits: true` は、依頼に含まれる場合だけ使う。

### 3. 編集を最小単位で行う

- 標準的なプリミティブ追加、モディファイア、原点設定などは、利用可能な専用操作または `bpy.ops` を使う。
- 精密な参照・データブロック操作・大量処理には `bpy.data` を使う。新しいデータ API オブジェクトは必ずコレクションへリンクする。
- 変更前に現在のモード、アクティブオブジェクト、選択状態、対象の実名を確認する。アクティブと選択は別物であり、オペレーターは副作用で選択を変える。
- 名前の衝突時に Blender が `.001` などを付けるため、作成直後の参照を保持する。推測した名前で後から探し直さない。
- 共有データブロックの `users` を確認する。共有メッシュやマテリアルを変更すると複数オブジェクトに影響するため、必要なら single-user 化してから変更する。
- 可能な限り直接メッシュを確定編集せず、モディファイアなど非破壊的な手段を優先する。
- 関連する変更を `execute_blender_code` でまとめる場合も、処理の最後に対象の状態を返す。途中で失敗し得る大きな一括処理や、対象不明の全削除は避ける。

### 4. 変更後に読み戻す

変更が終わったら、少なくとも次を実行する。

- `mcp__blender__get_object_detail_summary` または `mcp__blender__get_objects_summary` で、名前、位置、スケール、親子、モディファイア、マテリアル、可視性などの期待値を確認する。
- ジオメトリやモディファイアの評価値を読む場合は、依存グラフを更新してから読む。
- 見た目が重要な場合は `mcp__blender__get_screenshot_of_area_as_image`、`mcp__blender__render_thumbnail_to_path`、または `mcp__blender__render_viewport_to_path` を使う。メタデータだけで見た目を断定しない。
- レンダーや画像を生成した場合は、絶対パスと生成成否を報告する。必要なら出力画像をユーザーに提示する。

## `bpy` 実行時の規則

`execute_blender_code` に渡すコードは、短く検査可能な Python とする。`print` のログではなく、JSON 化できる辞書またはリストを `result` に代入して返す。

```python
import bpy

name = "Target"
obj = bpy.data.objects.get(name)
if obj is None:
    result = {"ok": False, "reason": "object_not_found", "name": name}
else:
    result = {
        "ok": True,
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation_mode": obj.rotation_mode,
        "scale": list(obj.scale),
        "users": getattr(obj.data, "users", None),
    }
```

編集時の注意:

- 回転は `rotation_mode` を確認してから、Euler、Quaternion、または Axis-Angle の正しいプロパティへ書き込む。
- ローカル座標とワールド座標を区別し、ワールド位置は必要に応じて `obj.matrix_world` から読む。親付きオブジェクトでは `location` をワールド位置とみなさない。
- 非均一スケールを残したままブーリアンや物理計算を行わない。必要な場合は、適用が破壊的変更にならないか確認してから処理する。
- Edit Mode のメッシュは通常の `mesh.vertices` 直接編集ではなく `bmesh` を使い、最後に更新・書き戻しする。モードを勝手に変更した場合は元の状態を維持できるか確認する。
- オペレーターに依存する場合は、対象を明示的に active・selected に設定し、必要なモードとコンテキストを整えてから一度だけ実行する。
- データ API で作成したオブジェクトは、作成しただけでは表示されない。対象コレクションへリンクする。
- 外部ファイル、既存の `.blend`、ライブラリ、テクスチャ、キャッシュを上書きしない。明示的な保存依頼がある場合でも、出力パスを確認してから保存する。

## ツールの使い分け

| 目的 | 使うツール |
| --- | --- |
| コレクションとオブジェクトの一覧 | `mcp__blender__get_objects_summary` |
| 特定オブジェクトの詳細 | `mcp__blender__get_object_detail_summary` |
| ファイルの保存状態・パス | `mcp__blender__get_blendfile_summary_path_info` |
| データブロック数・ワークスペース・レンダーエンジン | `mcp__blender__get_blendfile_summary_datablocks` |
| 欠落した画像・フォント・ライブラリなど | `mcp__blender__get_blendfile_summary_missing_files` |
| リンクされたライブラリの階層 | `mcp__blender__get_blendfile_summary_of_linked_libraries` |
| ウィンドウやエリアの状態 | `mcp__blender__get_screenshot_of_window_as_json` |
| 画面の画像 | `mcp__blender__get_screenshot_of_window_as_image` / `mcp__blender__get_screenshot_of_area_as_image` |
| ワークスペースや 3D ビューの移動 | `mcp__blender__jump_to_tab_by_name` / `mcp__blender__jump_to_tab_by_space_type` / `mcp__blender__jump_to_view3d_object_by_name` |
| 小さな確認用画像 | `mcp__blender__render_thumbnail_to_path` |
| 現在のレンダー設定での出力 | `mcp__blender__render_viewport_to_path` |
| Blender Python API の識別子 | `mcp__blender__get_python_api_docs` |
| API の全文検索 | `mcp__blender__search_api_docs` |
| Blender Manual の全文検索 | `mcp__blender__search_manual_docs` |
| 接続中の Blender へコード実行 | `mcp__blender__execute_blender_code` |
| 明示された `.blend` のバックグラウンド処理 | `mcp__blender__execute_blender_code_for_cli` |

API の使い方、オペレーターの引数、列挙値、モディファイアの仕様が曖昧なときは、推測でコードを書かず `mcp__blender__get_python_api_docs` または `mcp__blender__search_api_docs` を先に使う。概念的な操作手順は `mcp__blender__search_manual_docs` で確認する。

## トラブルシューティング

- MCP が応答しない場合は Blender の起動、MCP アドオンの接続、対象ファイルが開いているかを確認する。接続エラーを理由に、別のファイルや別の Blender プロセスを推測して操作しない。
- タイムアウト後は、同じ編集を盲目的に再実行しない。まず `get_objects_summary` または対象詳細を読み、変更が既に反映されていないか確認する。
- オペレーターが失敗したら、モード、アクティブオブジェクト、選択、可視性、コレクションの除外状態を再確認する。コンテキストを直さずに繰り返さない。
- オブジェクトが見えないときは、ビューポート非表示、View Layer での除外、レンダー無効の三つを区別して確認する。
- API の不明点は MCP に含まれる `data/api/` や `data/manual/` の検索ツールで調べる。外部 Web の説明を無検証でコードへ転記しない。

## 応答形式

作業後は、日本語で次の順に簡潔に報告する。

1. 検査または変更した対象（シーン名、オブジェクト名、必要ならデータブロック名）。
2. 実行した内容と、読み戻しで確認できた結果。
3. スクリーンショット・レンダー・保存ファイルの絶対パス。
4. 保存したかどうか。読み取り専用なら「シーンの変更は行っていない」と明記する。
5. エラーや未確認事項がある場合は、推測で埋めずに具体的に記載する。

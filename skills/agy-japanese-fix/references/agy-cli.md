# agy CLI リファレンス

2026-10-04 時点の実測メモ。差異があれば `agy --help` を正とする。

## 導入

```bash
npm i -g @google/antigravity
agy login
agy models
```

## 実行

- one-shot: `agy -p "prompt" [--model <name>] --sandbox --print-timeout "120s"`
- プロンプトは本文込みで `-p` に渡す。位置引数や stdin だけでは読まれない
- エージェント側のサンドボックス内では起動に失敗する（log 作成や bind が operation not permitted）。サンドボックス外で実行する

## 終了コード

- 0: 成功
- 3: 認証切れ → `agy login` を案内
- 4: 利用枠超過
- 5: タイムアウト（スクリプトが 124 を変換）
- 6: 出力が空（スクリプト独自）
- 10: agy 不在（スクリプト独自）

#!/usr/bin/env bash
# agy_fix.sh - Antigravity CLI を使った日本語校正ラッパー
# 生の agy 呼び出しではなく、このスクリプト経由で実行する。
#
# 使い方:
#   agy_fix.sh --style general|academic|business --input <file> --output <file> [--model auto] [--timeout 120]
#
set -euo pipefail

STYLE="general"
INPUT=""
OUTPUT=""
MODEL="auto"
TIMEOUT_SEC=120
SANDBOX_ARGS="--sandbox"

usage() {
  cat <<USAGE_EOF
Usage: agy_fix.sh --input <file> --output <file> [options]

Options:
  --style general|academic|business  文体プリセット
  --input FILE     校正対象の日本語テキストファイル
  --output FILE    校正結果の出力先ファイル
  --model NAME     agy に渡すモデル名
  --timeout SEC    タイムアウト秒数
USAGE_EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --style) STYLE="$2"; shift 2 ;;
    --input) INPUT="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --timeout) TIMEOUT_SEC="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$INPUT" ] || [ -z "$OUTPUT" ]; then
  echo "--input と --output は必須です" >&2
  usage >&2
  exit 2
fi

if [ ! -f "$INPUT" ]; then
  echo "入力ファイルが見つかりません" >&2
  exit 2
fi

case "$STYLE" in
  general|academic|business) ;;
  *) echo "--style は general|academic|business にしてください" >&2; exit 2 ;;
esac

if ! command -v agy >/dev/null 2>&1; then
  echo "agy が見つかりません。references/agy-cli.md を確認してください。" >&2
  exit 10
fi

WORK_DIR="$(mktemp -d)"
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT
cp "$INPUT" "$WORK_DIR/input.txt"

STYLE_RULE="原文の文体を維持し、読みやすさだけ改善する。"
if [ "$STYLE" = "academic" ]; then
  STYLE_RULE="文体はである調に統一し、句読点は全角にする。学術論文として整える。"
fi
if [ "$STYLE" = "business" ]; then
  STYLE_RULE="文体はですます調に統一し、敬語と表記ゆれを整える。"
fi

cat > "$WORK_DIR/prompt.txt" <<PROMPT_EOF
あなたは日本語校正者です。以下の日本語文章だけを校正してください。
制約:
- 誤字脱字・送り仮名・助詞・接続詞・主語述語の対応を修正する
- 数値・固有名詞・引用・LaTeXコマンド・Markdown構造は原文どおり保持する
- 意味・因果関係・主張の強さを変えない。情報を追加しない
- 意味が確定しない箇所は無理に直さず残す
- 出力は校正後の日本語本文だけにする
PROMPT_EOF
echo "$STYLE_RULE" >> "$WORK_DIR/prompt.txt"
echo "対象ファイル: $WORK_DIR/input.txt" >> "$WORK_DIR/prompt.txt"

BASE_PROMPT="$(cat "$WORK_DIR/prompt.txt")"
INPUT_BODY="$(cat "$WORK_DIR/input.txt")"
NL="$(printf "\n")"
COMBINED_PROMPT="$BASE_PROMPT$NL---校正対象---$NL$INPUT_BODY"

set +e
MODEL_ARGS=""
if [ "$MODEL" != "auto" ]; then
  MODEL_ARGS="--model $MODEL"
fi
agy -p "$COMBINED_PROMPT" $MODEL_ARGS --sandbox --print-timeout "${TIMEOUT_SEC}s" > "$WORK_DIR/fixed.txt" 2>"$WORK_DIR/stderr.log"
STATUS=$?
set -e

if [ $STATUS -eq 124 ]; then
  echo "agy がタイムアウトしました。フォールバック校正に切り替えてください。" >&2
  exit 5
fi

if [ $STATUS -ne 0 ]; then
  echo "agy 実行に失敗しました。" >&2
  cat "$WORK_DIR/stderr.log" >&2 || true
  exit $STATUS
fi

if [ ! -s "$WORK_DIR/fixed.txt" ]; then
  echo "agy の出力が空でした。" >&2
  exit 6
fi

OUTDIR="$(dirname "$OUTPUT")"
mkdir -p "$OUTDIR"
cp "$WORK_DIR/fixed.txt" "$OUTPUT"
echo "校正結果を保存しました"

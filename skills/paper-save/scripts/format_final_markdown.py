#!/usr/bin/env python3
"""Normalize numbered ATX levels and spacing in a final paper-save note."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)")
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
NUMBERED_HEADING_RE = re.compile(
    r"^(?P<indent> {0,3})#{1,6}(?P<space>[ \t]+)"
    r"(?P<number>\d+(?:\.\d+)*)(?P<suffix>\.?(?:[ \t]+.*)?$)"
)


class FormatError(RuntimeError):
    """Raised when the final Markdown cannot be formatted safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def normalize_numbered_heading_level(line: str) -> str:
    match = NUMBERED_HEADING_RE.match(line)
    if match is None:
        return line

    depth = match.group("number").count(".") + 1
    markdown_level = depth + 1
    if markdown_level > 6:
        raise FormatError(
            f"番号付き見出しがMarkdownの最大階層を超えています: {line}"
        )

    return (
        f'{match.group("indent")}{"#" * markdown_level}'
        f'{match.group("space")}{match.group("number")}{match.group("suffix")}'
    )


def normalize_heading_spacing(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    active_fence: str | None = None
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    after_heading = False
    has_body_content = False

    for index, line in enumerate(lines):
        if in_frontmatter:
            output.append(line)
            if index > 0 and line.strip() == "---":
                in_frontmatter = False
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            if after_heading:
                output.append("")
                after_heading = False
            fence = fence_match.group("fence")
            if active_fence is None:
                active_fence = fence[0]
            elif active_fence == fence[0]:
                active_fence = None
            output.append(line)
            has_body_content = True
            continue

        is_heading = active_fence is None and HEADING_RE.match(line) is not None
        if is_heading:
            line = normalize_numbered_heading_level(line)
            while output and output[-1].strip() == "":
                output.pop()
            if has_body_content:
                output.append("")
            output.append(line)
            after_heading = True
            has_body_content = True
            continue

        if after_heading:
            if line.strip() == "":
                continue
            output.append("")
            after_heading = False

        output.append(line)
        if line.strip():
            has_body_content = True

    if in_frontmatter:
        raise FormatError("YAML frontmatterが閉じられていません")

    while output and output[-1] == "":
        output.pop()
    return "\n".join(output) + "\n"


def run(args: argparse.Namespace) -> int:
    if not args.input.is_file():
        raise FormatError(f"入力Markdownが見つかりません: {args.input}")
    if args.output.exists():
        raise FormatError(f"出力Markdownが既に存在します: {args.output}")

    text = args.input.read_text(encoding="utf-8")
    formatted = normalize_heading_spacing(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(formatted, encoding="utf-8")
    print(f"Markdown: {args.output}")
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except (OSError, UnicodeError, FormatError) as exc:
        print(f"paper-save: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate final Markdown headings against a PDF-derived heading map."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


HEADING_RE = re.compile(r"^ {0,3}(?P<marks>#{1,6})(?:[ \t]+(?P<title>.*)|[ \t]*)$")
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
TRAILING_MARKS_RE = re.compile(r"[ \t]+#+[ \t]*$")
GENERATED_TRAILING_HEADINGS = [(2, "PDF"), (2, "BibTeX")]


class ValidationError(RuntimeError):
    """Raised when Markdown headings do not match the PDF-derived map."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    return parser.parse_args()


def extract_headings(text: str) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []
    active_fence: str | None = None
    in_frontmatter = False

    for index, line in enumerate(text.splitlines()):
        if index == 0 and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
            continue

        fence_match = FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group("fence")
            if active_fence is None:
                active_fence = fence[0]
            elif active_fence == fence[0]:
                active_fence = None
            continue
        if active_fence is not None:
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match is None:
            continue
        title = TRAILING_MARKS_RE.sub("", heading_match.group("title") or "").strip()
        if not title:
            raise ValidationError(f"空のATX見出しがあります: {index + 1}行目")
        headings.append((len(heading_match.group("marks")), title))

    if in_frontmatter:
        raise ValidationError("YAML frontmatterが閉じられていません")
    if active_fence is not None:
        raise ValidationError("コードフェンスが閉じられていません")

    for generated in reversed(GENERATED_TRAILING_HEADINGS):
        if headings and headings[-1] == generated:
            headings.pop()
        else:
            raise ValidationError(f"末尾に ## {generated[1]} がありません")
    return headings


def load_expected(path: Path) -> list[tuple[int, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"heading mapがJSONとして不正です: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("headings"), list):
        raise ValidationError('heading mapは {"headings": [...]} 形式にしてください')

    expected: list[tuple[int, str]] = []
    for index, item in enumerate(data["headings"], start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"heading mapの項目{index}がオブジェクトではありません")
        level = item.get("level")
        title = item.get("title")
        if not isinstance(level, int) or not 2 <= level <= 6:
            raise ValidationError(f"heading mapの項目{index}のlevelが不正です")
        if not isinstance(title, str) or not title.strip():
            raise ValidationError(f"heading mapの項目{index}のtitleが不正です")
        expected.append((level, title.strip()))
    return expected


def compare_headings(
    actual: list[tuple[int, str]], expected: list[tuple[int, str]]
) -> None:
    for index, (actual_item, expected_item) in enumerate(
        zip(actual, expected), start=1
    ):
        if actual_item != expected_item:
            raise ValidationError(
                f"見出し{index}が不一致です: "
                f"expected={'#' * expected_item[0]} {expected_item[1]!r}, "
                f"actual={'#' * actual_item[0]} {actual_item[1]!r}"
            )
    if len(actual) != len(expected):
        raise ValidationError(
            f"見出し数が不一致です: expected={len(expected)}, actual={len(actual)}"
        )


def run(args: argparse.Namespace) -> int:
    if not args.markdown.is_file():
        raise ValidationError(f"Markdownが見つかりません: {args.markdown}")
    if not args.expected.is_file():
        raise ValidationError(f"heading mapが見つかりません: {args.expected}")

    actual = extract_headings(args.markdown.read_text(encoding="utf-8"))
    expected = load_expected(args.expected)
    compare_headings(actual, expected)
    print(f"Headings: {len(actual)}")
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except (OSError, UnicodeError, ValidationError) as exc:
        print(f"paper-save: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

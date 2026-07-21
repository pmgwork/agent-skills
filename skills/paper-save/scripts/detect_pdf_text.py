#!/usr/bin/env python3
"""Classify a PDF for Docling OCR mode using its first three pages."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


class DetectionError(RuntimeError):
    """Raised when PDF text detection cannot be completed."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    return parser.parse_args()


def classify(character_count: int) -> str:
    if character_count == 0:
        return "ocr"
    return "no-ocr"


def print_no_ocr_fallback(reason: str) -> int:
    print("OCR mode: no-ocr")
    print(f"Reason: {reason}; using default")
    return 0


def run(args: argparse.Namespace) -> int:
    if not args.pdf.is_file() or args.pdf.stat().st_size == 0:
        raise DetectionError(f"PDFが見つからないか空です: {args.pdf}")
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        return print_no_ocr_fallback("pdftotext is not available")
    result = subprocess.run(
        [pdftotext, "-f", "1", "-l", "3", str(args.pdf), "-"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        return print_no_ocr_fallback(f"pdftotext failed: {detail}")
    character_count = sum(not character.isspace() for character in result.stdout)
    print(f"OCR mode: {classify(character_count)}")
    print(f"Non-whitespace characters: {character_count}")
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except (OSError, UnicodeError, DetectionError) as exc:
        print(f"paper-save: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

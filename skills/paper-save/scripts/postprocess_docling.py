#!/usr/bin/env python3
"""Prepare Docling Markdown and image artifacts for an Obsidian paper note."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


IMAGE_RE = re.compile(
    r"!\[[^\]]*\]\((?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?\)"
)
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")


class PostprocessError(RuntimeError):
    """Raised when Docling output cannot be transformed safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path)
    parser.add_argument("--artifacts-dir", required=True, type=Path)
    parser.add_argument("--output-markdown", required=True, type=Path)
    parser.add_argument("--output-artifacts-dir", required=True, type=Path)
    parser.add_argument("--asset-link-prefix", required=True)
    return parser.parse_args()


def validate_inputs(
    markdown: Path,
    artifacts_dir: Path,
    output_markdown: Path,
    output_artifacts_dir: Path,
    asset_link_prefix: str,
) -> None:
    if not markdown.is_file():
        raise PostprocessError(f"Markdownが見つかりません: {markdown}")
    if artifacts_dir.exists() and not artifacts_dir.is_dir():
        raise PostprocessError(f"artifactsの指定先がフォルダではありません: {artifacts_dir}")
    if output_markdown.exists():
        raise PostprocessError(f"出力Markdownが既に存在します: {output_markdown}")
    if output_artifacts_dir.exists() and any(output_artifacts_dir.iterdir()):
        raise PostprocessError(f"出力artifactsフォルダが空ではありません: {output_artifacts_dir}")

    prefix = Path(asset_link_prefix)
    if prefix.is_absolute() or ".." in prefix.parts or not prefix.parts:
        raise PostprocessError("asset link prefixはvault相対パスで指定してください")

    non_png = sorted(
        path.name
        for path in (artifacts_dir.iterdir() if artifacts_dir.exists() else ())
        if path.is_file() and path.suffix.lower() != ".png"
    )
    if non_png:
        raise PostprocessError(f"PNG以外のartifactがあります: {', '.join(non_png)}")


def resolve_image(reference: str, markdown: Path, artifacts_dir: Path) -> Path:
    split = urlsplit(reference)
    if split.scheme or split.netloc:
        raise PostprocessError(f"外部画像参照は変換できません: {reference}")

    decoded = unquote(split.path)
    candidate = Path(decoded)
    if not candidate.is_absolute():
        candidate = markdown.parent / candidate
    candidate = candidate.resolve()
    artifacts_root = artifacts_dir.resolve()

    try:
        candidate.relative_to(artifacts_root)
    except ValueError:
        fallback = (artifacts_root / Path(decoded).name).resolve()
        try:
            fallback.relative_to(artifacts_root)
        except ValueError as exc:
            raise PostprocessError(f"artifacts外の画像参照です: {reference}") from exc
        candidate = fallback

    if not candidate.is_file():
        raise PostprocessError(f"参照画像が見つかりません: {reference}")
    if candidate.suffix.lower() != ".png":
        raise PostprocessError(f"PNG以外の画像参照です: {reference}")
    return candidate


def transform(
    text: str,
    markdown: Path,
    artifacts_dir: Path,
    asset_link_prefix: str,
) -> tuple[str, list[tuple[Path, str]]]:
    assignments: dict[Path, str] = {}
    ordered: list[tuple[Path, str]] = []

    def assign(source: Path) -> str:
        source = source.resolve()
        if source not in assignments:
            filename = f"image_{len(assignments) + 1:03d}.png"
            assignments[source] = filename
            ordered.append((source, filename))
        return assignments[source]

    def replace_image(match: re.Match[str]) -> str:
        reference = match.group("angle") or match.group("plain")
        source = resolve_image(reference, markdown, artifacts_dir)
        return f"![[{asset_link_prefix.rstrip('/')}/{assign(source)}]]"

    output_lines: list[str] = []
    active_fence: str | None = None

    for line in text.splitlines(keepends=True):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group("fence")
            if active_fence is None:
                active_fence = fence[0]
            elif active_fence == fence[0]:
                active_fence = None
            output_lines.append(line)
            continue

        if active_fence is None:
            line = IMAGE_RE.sub(replace_image, line)
        output_lines.append(line)

    artifact_paths = artifacts_dir.iterdir() if artifacts_dir.exists() else ()
    for source in sorted(artifact_paths, key=lambda path: path.name):
        if source.is_file() and source.suffix.lower() == ".png":
            assign(source)

    return "".join(output_lines), ordered


def run(args: argparse.Namespace) -> int:
    validate_inputs(
        args.markdown,
        args.artifacts_dir,
        args.output_markdown,
        args.output_artifacts_dir,
        args.asset_link_prefix,
    )
    text = args.markdown.read_text(encoding="utf-8")
    transformed, artifacts = transform(text, args.markdown, args.artifacts_dir, args.asset_link_prefix)

    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_artifacts_dir.parent.mkdir(parents=True, exist_ok=True)
    stage_root = Path(
        tempfile.mkdtemp(prefix=".paper-save-postprocess-", dir=args.output_markdown.parent)
    )
    stage_markdown = stage_root / "prepared.md"
    stage_artifacts = stage_root / "artifacts"
    stage_artifacts.mkdir()
    committed_artifacts = False
    try:
        for source, filename in artifacts:
            shutil.copy2(source, stage_artifacts / filename)
        stage_markdown.write_text(transformed, encoding="utf-8")

        if args.output_artifacts_dir.exists():
            args.output_artifacts_dir.rmdir()
        os.replace(stage_artifacts, args.output_artifacts_dir)
        committed_artifacts = True
        os.replace(stage_markdown, args.output_markdown)
    except Exception:
        if committed_artifacts and args.output_artifacts_dir.exists():
            try:
                os.replace(args.output_artifacts_dir, stage_artifacts)
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)
    print(f"Markdown: {args.output_markdown}")
    print(f"Artifacts: {len(artifacts)}")
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except (OSError, UnicodeError, PostprocessError) as exc:
        print(f"paper-save: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

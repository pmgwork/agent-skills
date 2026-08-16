#!/usr/bin/env python3
"""
Save paper note, PDF, and image artifacts to Obsidian vault in a single atomic step.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Regex patterns for image link transformation and markdown cleanup
MARKDOWN_IMAGE_RE = re.compile(
    r"!\[[^\]]*\]\((?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?\)"
)
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")


class PaperSaveError(RuntimeError):
    """Raised when paper saving cannot be completed safely."""


def get_vault_root() -> Path:
    """Get vault root directory from PAPER_SAVE_VAULT_ROOT environment variable."""
    env_root = os.environ.get("PAPER_SAVE_VAULT_ROOT")
    if not env_root:
        raise PaperSaveError(
            "環境変数 PAPER_SAVE_VAULT_ROOT が設定されていません。\n"
            "以下のコマンドを実行して設定し、完了したら再度実行してください:\n"
            '  echo "export PAPER_SAVE_VAULT_ROOT=\\"<Obsidian Vaultの絶対パス>\\"" >> ~/.zshrc\n'
            "  source ~/.zshrc"
        )
    candidate = Path(env_root).expanduser().resolve()
    if not candidate.is_dir():
        raise PaperSaveError(f"PAPER_SAVE_VAULT_ROOT で指定されたディレクトリが存在しません: {candidate}")
    return candidate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True, help="Official paper title")
    parser.add_argument("--pdf", required=True, type=Path, help="Path to original PDF file")
    parser.add_argument("--markdown", required=True, type=Path, help="Path to formatted note markdown")
    parser.add_argument("--docling-artifacts", type=Path, help="Path to Docling extracted artifacts directory")
    parser.add_argument("--check-only", action="store_true", help="Only check for name conflicts without saving")
    return parser.parse_args()


def sanitize_title(title: str) -> str:
    """Sanitize title for filesystem usage while preserving words and casing."""
    # Remove invalid filesystem characters
    cleaned = re.sub(r'[/\\*?"<>|]', "", title)
    # Replace separators with a space
    cleaned = re.sub(r"[:\-\u2013\u2014]", " ", cleaned)
    # Remove punctuation, apostrophes, quotes, brackets
    cleaned = re.sub(r"[.,'\"`\(\)\[\]\{\}]", "", cleaned)
    # Collapse multiple spaces and strip
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or cleaned in {".", ".."}:
        raise PaperSaveError(f"Sanitized title is invalid or empty: '{cleaned}' from '{title}'")
    return cleaned


def check_conflicts(papers_dir: Path, sanitized_title: str) -> None:
    """Check if destination note or non-empty assets directory already exists."""
    papers_dir.mkdir(parents=True, exist_ok=True)
    note_path = papers_dir / f"{sanitized_title}.md"
    assets_dir = papers_dir / "assets" / sanitized_title

    if note_path.exists():
        raise PaperSaveError(f"Target note already exists: {note_path}")
    if assets_dir.exists() and any(assets_dir.iterdir()):
        raise PaperSaveError(f"Target assets directory already exists and is not empty: {assets_dir}")


def transform_and_collect_images(
    text: str,
    markdown_dir: Path,
    artifacts_dir: Path | None,
    sanitized_title: str,
) -> tuple[str, list[tuple[Path, str]]]:
    """Transform markdown image links to Obsidian wikilinks and assign numbered filenames."""
    assignments: dict[Path, str] = {}
    ordered_images: list[tuple[Path, str]] = []
    asset_prefix = f"assets/{sanitized_title}/artifacts"

    def resolve_image(reference: str) -> Path:
        split = urlsplit(reference)
        decoded = unquote(split.path)
        candidate = Path(decoded)
        if not candidate.is_absolute():
            candidate = markdown_dir / candidate
        candidate = candidate.resolve()

        if artifacts_dir:
            artifacts_root = artifacts_dir.resolve()
            try:
                candidate.relative_to(artifacts_root)
            except ValueError:
                fallback = (artifacts_root / Path(decoded).name).resolve()
                try:
                    fallback.relative_to(artifacts_root)
                except ValueError:
                    pass
                else:
                    candidate = fallback

        if not candidate.is_file():
            raise PaperSaveError(f"Referenced image file not found: {reference}")
        return candidate

    def assign(source_path: Path) -> str:
        source_path = source_path.resolve()
        if source_path not in assignments:
            filename = f"image_{len(assignments) + 1:03d}.png"
            assignments[source_path] = filename
            ordered_images.append((source_path, filename))
        return assignments[source_path]

    def replace_image_match(match: re.Match[str]) -> str:
        ref = match.group("angle") or match.group("plain")
        source_file = resolve_image(ref)
        assigned_name = assign(source_file)
        return f"![[{asset_prefix}/{assigned_name}]]"

    # Line-by-line transformation ignoring code blocks
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
            line = MARKDOWN_IMAGE_RE.sub(replace_image_match, line)
        output_lines.append(line)

    # If there are unused PNG artifacts, keep them indexed too
    if artifacts_dir and artifacts_dir.is_dir():
        for artifact in sorted(artifacts_dir.glob("*.png")):
            if artifact.is_file():
                assign(artifact)

    return "".join(output_lines), ordered_images


def save_paper(
    vault_root: Path,
    title: str,
    pdf_path: Path,
    markdown_path: Path,
    artifacts_dir: Path | None,
) -> tuple[Path, Path, int]:
    """Atomically save note, PDF, and artifacts to Obsidian vault."""
    if not vault_root.is_dir():
        raise PaperSaveError(f"Vault root directory not found: {vault_root}")
    if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        raise PaperSaveError(f"Original PDF not found or is empty: {pdf_path}")
    if not markdown_path.is_file() or markdown_path.stat().st_size == 0:
        raise PaperSaveError(f"Markdown note not found or is empty: {markdown_path}")

    sanitized = sanitize_title(title)
    papers_dir = vault_root / "papers"
    check_conflicts(papers_dir, sanitized)

    raw_text = markdown_path.read_text(encoding="utf-8")
    transformed_text, images = transform_and_collect_images(
        raw_text,
        markdown_path.parent,
        artifacts_dir,
        sanitized,
    )

    # Destination paths
    final_note = papers_dir / f"{sanitized}.md"
    final_assets = papers_dir / "assets" / sanitized
    final_pdf = final_assets / f"{sanitized}.pdf"
    final_artifacts = final_assets / "artifacts"

    created_paths: list[Path] = []
    try:
        final_assets.mkdir(parents=True, exist_ok=True)
        created_paths.append(final_assets)

        final_artifacts.mkdir(parents=True, exist_ok=True)
        created_paths.append(final_artifacts)

        # Copy PDF
        shutil.copy2(pdf_path, final_pdf)
        created_paths.append(final_pdf)

        # Copy Images
        for src, dest_name in images:
            dest_file = final_artifacts / dest_name
            shutil.copy2(src, dest_file)
            created_paths.append(dest_file)

        # Write Markdown note
        final_note.write_text(transformed_text, encoding="utf-8")
        created_paths.append(final_note)

    except Exception as exc:
        # Rollback on any failure
        for path in reversed(created_paths):
            if path.is_file():
                path.unlink(missing_ok=True)
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        raise PaperSaveError(f"Failed to save paper note: {exc}") from exc

    return final_note, final_pdf, len(images)


def main() -> int:
    args = parse_args()
    try:
        vault_root = get_vault_root()
        sanitized = sanitize_title(args.title)
        papers_dir = vault_root / "papers"

        if args.check_only:
            check_conflicts(papers_dir, sanitized)
            print(f"SanitizedTitle: {sanitized}")
            print(f"VaultRoot: {vault_root}")
            print("Conflict check: PASSED (No existing note or assets)")
            return 0

        note, pdf, image_count = save_paper(
            vault_root,
            args.title,
            args.pdf,
            args.markdown,
            args.docling_artifacts,
        )
        print(f"Saved Note: {note}")
        print(f"Saved PDF:  {pdf}")
        print(f"Saved Artifacts: {image_count} images")
        return 0
    except (OSError, UnicodeError, PaperSaveError) as exc:
        print(f"save-paper error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

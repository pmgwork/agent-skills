#!/usr/bin/env python3
"""Save a paper note, PDF, and image artifacts without overwriting existing work."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Regex patterns for image link transformation and markdown cleanup
IMAGE_START_RE = re.compile(r"!\[[^\]]*\]\(")
INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`)(.*?)(?<!`)\1(?!`)", re.DOTALL)
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
IMAGE_SUFFIXES = {
    ".avif", ".bmp", ".gif", ".heic", ".heif", ".jpeg", ".jpg",
    ".png", ".svg", ".tif", ".tiff", ".webp",
}


class PaperSaveError(RuntimeError):
    """Raised when paper saving cannot be completed safely."""


def replace_markdown_images(line: str, replace_reference) -> str:
    """Accept Docling's raw paths with spaces and balanced parentheses, too."""
    output: list[str] = []
    cursor = 0
    code_spans = [match.span() for match in INLINE_CODE_RE.finditer(line)]
    while match := IMAGE_START_RE.search(line, cursor):
        output.append(line[cursor:match.start()])
        if any(start <= match.start() < end for start, end in code_spans):
            output.append(match.group())
            cursor = match.end()
            continue
        start = match.end()
        if line[start:start + 1] == "<":
            end = line.find(">", start + 1)
            closing = re.match(r'''(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)''', line[end + 1:]) if end >= 0 else None
            if closing is None:
                raise PaperSaveError(f"Malformed image link: {line.strip()}")
            reference = line[start + 1:end]
            stop = end + 1 + closing.end()
        else:
            depth = 1
            end = start
            while end < len(line) and depth:
                if depth == 1 and line[end] in "\"'" and end > start and line[end - 1].isspace():
                    title = re.match(r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')\s*\)''', line[end:])
                    if title:
                        reference = line[start:end].strip()
                        end += title.end()
                        depth = 0
                        break
                if line[end] == "\\":
                    end += 2
                    continue
                if line[end] == "(":
                    depth += 1
                elif line[end] == ")":
                    depth -= 1
                end += 1
            else:
                reference = line[start:end - 1].strip()
            if depth:
                raise PaperSaveError(f"Malformed image link: {line.strip()}")
            reference = re.sub(r"\\([() ])", r"\1", reference)
            stop = end
        output.append(replace_reference(reference))
        cursor = stop
    output.append(line[cursor:])
    return "".join(output)


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
    """Check destinations without creating or changing anything."""
    note_path = papers_dir / f"{sanitized_title}.md"
    assets_dir = papers_dir / "assets" / sanitized_title

    if note_path.exists() or note_path.is_symlink():
        raise PaperSaveError(f"Target note already exists: {note_path}")
    if assets_dir.exists() or assets_dir.is_symlink():
        raise PaperSaveError(f"Target assets directory already exists: {assets_dir}")


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
        if reference.startswith("//") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", reference):
            split = urlsplit(reference)
            if split.scheme.lower() != "file" or split.netloc not in {"", "localhost"}:
                raise PaperSaveError(f"Image must be a local file; download it first: {reference}")
            paths = [Path(unquote(split.path))]
        else:
            # Raw Docling filenames take precedence over URL decoding (# and % are legal).
            paths = [Path(reference)]
            if unquote(reference) != reference:
                paths.append(Path(unquote(reference)))
        for path in paths:
            candidates = [path] if path.is_absolute() else [markdown_dir / path]
            if artifacts_dir and not path.is_absolute():
                candidates.append(artifacts_dir / path)
            for candidate in candidates:
                if candidate.is_file():
                    return candidate.resolve()
        raise PaperSaveError(f"Referenced image file not found: {reference}")

    def assign(source_path: Path) -> str:
        source_path = source_path.resolve()
        if source_path not in assignments:
            suffix = source_path.suffix.lower()
            if suffix not in IMAGE_SUFFIXES:
                raise PaperSaveError(f"Unsupported image format: {source_path}")
            filename = f"image_{len(assignments) + 1:03d}{suffix}"
            assignments[source_path] = filename
            ordered_images.append((source_path, filename))
        return assignments[source_path]

    def replace_image_reference(ref: str) -> str:
        source_file = resolve_image(ref)
        assigned_name = assign(source_file)
        return f"![[{asset_prefix}/{assigned_name}]]"

    # Line-by-line transformation ignoring code blocks
    output_lines: list[str] = []
    active_fence: tuple[str, int] | None = None
    pending: list[str] = []

    def flush_pending() -> None:
        output_lines.append(replace_markdown_images("".join(pending), replace_image_reference))
        pending.clear()

    frontmatter = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", text, re.DOTALL)
    header = frontmatter.group() if frontmatter else ""
    body = text[len(header):]

    for line in body.splitlines(keepends=True):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            flush_pending()
            fence = fence_match.group("fence")
            if active_fence is None:
                active_fence = (fence[0], len(fence))
            elif (
                active_fence[0] == fence[0]
                and len(fence) >= active_fence[1]
                and not line[fence_match.end():].strip()
            ):
                active_fence = None
            output_lines.append(line)
            continue

        if active_fence is None:
            pending.append(line)
        else:
            output_lines.append(line)
    flush_pending()

    # Keep every supported image artifact, including nested and unreferenced files.
    if artifacts_dir and artifacts_dir.is_dir():
        for artifact in sorted(artifacts_dir.rglob("*")):
            if artifact.is_file() and artifact.suffix.lower() in IMAGE_SUFFIXES:
                assign(artifact)

    def replace_figure(match: re.Match[str]) -> str:
        value = match.group(1).strip()
        if value.startswith('"'):
            try:
                reference = json.loads(value)
            except ValueError as exc:
                raise PaperSaveError("figure must be a quoted local image path") from exc
        elif value.startswith("'") and value.endswith("'"):
            reference = value[1:-1].replace("''", "'")
        else:
            reference = value
        if not isinstance(reference, str) or not reference:
            raise PaperSaveError("figure must be a local image path, or omit it")
        if reference.startswith(asset_prefix + "/"):
            filename = reference[len(asset_prefix) + 1:]
            names = list(assignments.values())
            if filename not in names:
                matches = [name for name in names if Path(name).stem == Path(filename).stem]
                if len(matches) != 1:
                    raise PaperSaveError(f"Thumbnail does not match a saved image: {reference}")
                filename = matches[0]
        else:
            filename = assign(resolve_image(reference))
        return "figure: " + json.dumps(f"{asset_prefix}/{filename}", ensure_ascii=False)

    header = re.sub(r"^figure:[ \t]*(.*)$", replace_figure, header, flags=re.MULTILINE)
    return header + "".join(output_lines), ordered_images


def save_paper(
    vault_root: Path,
    title: str,
    pdf_path: Path,
    markdown_path: Path,
    artifacts_dir: Path | None,
) -> tuple[Path, Path, int]:
    """Save a paper while reserving its assets directory exclusively.

    The assets directory is reserved with an atomic mkdir, and the note is
    published only after every asset has been copied. The note and assets are
    separate filesystem paths, so the complete operation is not one atomic
    filesystem transaction.
    """
    if not vault_root.is_dir():
        raise PaperSaveError(f"Vault root directory not found: {vault_root}")
    if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
        raise PaperSaveError(f"Original PDF not found or is empty: {pdf_path}")
    if not markdown_path.is_file() or markdown_path.stat().st_size == 0:
        raise PaperSaveError(f"Markdown note not found or is empty: {markdown_path}")
    if artifacts_dir is not None and not artifacts_dir.is_dir():
        raise PaperSaveError(f"Docling artifacts directory not found: {artifacts_dir}")

    sanitized = sanitize_title(title)
    papers_dir = vault_root / "papers"
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

    papers_dir.mkdir(parents=True, exist_ok=True)
    (papers_dir / "assets").mkdir(exist_ok=True)
    check_conflicts(papers_dir, sanitized)

    reserved_assets = False
    note_published = False
    try:
        # mkdir without exist_ok is the cross-process reservation for this title.
        final_assets.mkdir()
        reserved_assets = True

        # Recheck after reservation to close the note-creation race.
        if final_note.exists() or final_note.is_symlink():
            raise PaperSaveError(f"Target note already exists: {final_note}")

        final_artifacts.mkdir()

        # Copy PDF
        shutil.copy2(pdf_path, final_pdf)

        # Copy Images
        for src, dest_name in images:
            dest_file = final_artifacts / dest_name
            shutil.copy2(src, dest_file)

        # Write out of sight, then publish with an atomic, no-overwrite hard link.
        temporary_note = final_assets / ".note.md.tmp"
        with temporary_note.open("x", encoding="utf-8") as note_file:
            note_file.write(transformed_text)
        os.link(temporary_note, final_note)
        note_published = True
        try:
            temporary_note.unlink()
        except OSError:
            # The published note is complete; a hidden duplicate is harmless.
            pass

    except Exception as exc:
        # Only remove the directory that this invocation reserved itself.
        if reserved_assets and not note_published:
            shutil.rmtree(final_assets)
        if isinstance(exc, PaperSaveError):
            raise
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

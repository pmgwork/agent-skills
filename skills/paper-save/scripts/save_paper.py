#!/usr/bin/env python3
"""Format, minimally validate, and save a paper-save note."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path


HEADING_RE = re.compile(r"^ {0,3}#{1,6}(?:[ \t]+|$)")
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
NUMBERED_HEADING_RE = re.compile(
    r"^(?P<indent> {0,3})#{1,6}(?P<space>[ \t]+)"
    r"(?P<number>\d+(?:\.\d+)*)(?P<suffix>\.?(?:[ \t]+.*)?$)"
)
FIGURE_LINE_RE = re.compile(r"^figure:.*$", re.MULTILINE)
FIGURE_RE = re.compile(r'^figure:\s*"(?P<path>[^"]+)"\s*$', re.MULTILINE)
WIKI_PDF_RE = re.compile(r"!\[\[(?P<path>[^\]\n]+\.pdf)\]\]", re.IGNORECASE)
WIKI_IMAGE_RE = re.compile(r"!\[\[(?P<path>[^\]\n]+\.png)\]\]", re.IGNORECASE)
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(")


class SaveError(RuntimeError):
    """Raised when a paper cannot be saved safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--papers-dir", required=True, type=Path)
    parser.add_argument("--sanitized-title", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--paper-pdf", type=Path)
    parser.add_argument("--artifacts-dir", type=Path)
    return parser.parse_args()


def validate_name(papers_dir: Path, title: str) -> None:
    if not title or title in {".", ".."} or "/" in title or "\\" in title:
        raise SaveError("SanitizedTitleが空または不正です")
    try:
        name_max = os.pathconf(papers_dir, "PC_NAME_MAX")
    except (OSError, ValueError):
        name_max = 255
    candidates = [f"{title}.md", title, f"{title}.pdf"]
    if any(len(candidate.encode("utf-8")) > name_max for candidate in candidates):
        raise SaveError(
            f"SanitizedTitleがファイルシステムの名前上限を超えます: {name_max} bytes"
        )


def extract_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---", 4)
    return text[4:end] if end >= 0 else ""


def check_conflicts(papers_dir: Path, title: str) -> None:
    if not papers_dir.is_dir():
        raise SaveError(f"papersフォルダが見つかりません: {papers_dir}")
    validate_name(papers_dir, title)

    note = papers_dir / f"{title}.md"
    assets = papers_dir / "assets" / title
    if note.exists():
        raise SaveError(f"登録先が既に存在します: {note}")
    if assets.exists():
        if not assets.is_dir() or any(path.is_file() for path in assets.rglob("*")):
            raise SaveError(f"登録先が既に存在します: {assets}")


def normalize_numbered_heading_level(line: str) -> str:
    match = NUMBERED_HEADING_RE.match(line)
    if match is None:
        return line
    markdown_level = match.group("number").count(".") + 2
    if markdown_level > 6:
        raise SaveError(f"番号付き見出しがMarkdownの最大階層を超えています: {line}")
    return (
        f'{match.group("indent")}{"#" * markdown_level}'
        f'{match.group("space")}{match.group("number")}{match.group("suffix")}'
    )


def format_markdown(text: str) -> str:
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

        if active_fence is None and HEADING_RE.match(line):
            line = normalize_numbered_heading_level(line)
            while output and not output[-1].strip():
                output.pop()
            if has_body_content:
                output.append("")
            output.append(line)
            after_heading = True
            has_body_content = True
            continue

        if after_heading:
            if not line.strip():
                continue
            output.append("")
            after_heading = False
        output.append(line)
        if line.strip():
            has_body_content = True

    if in_frontmatter:
        raise SaveError("YAML frontmatterが閉じられていません")
    while output and not output[-1]:
        output.pop()
    return "\n".join(output) + "\n"


def outside_fenced_blocks(text: str) -> str:
    output: list[str] = []
    active_fence: str | None = None
    for line in text.splitlines():
        fence_match = FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group("fence")
            if active_fence is None:
                active_fence = fence[0]
            elif active_fence == fence[0]:
                active_fence = None
            continue
        if active_fence is None:
            output.append(line)
    return "\n".join(output)


def require_nonempty_file(path: Path | None, label: str) -> Path:
    if path is None or not path.is_file() or path.stat().st_size == 0:
        raise SaveError(f"{label}が見つからないか空です: {path}")
    return path


def validate_inputs(
    text: str, paper_pdf: Path | None, artifacts_dir: Path | None, title: str
) -> tuple[Path, list[Path]]:
    pdf = require_nonempty_file(paper_pdf, "原本PDF")
    if artifacts_dir is None or not artifacts_dir.is_dir():
        raise SaveError(f"artifactsフォルダがありません: {artifacts_dir}")
    artifacts = sorted(path for path in artifacts_dir.iterdir() if path.is_file())
    non_png = [path.name for path in artifacts if path.suffix.lower() != ".png"]
    if non_png:
        raise SaveError(f"PNG以外のartifactがあります: {', '.join(non_png)}")
    empty = [path.name for path in artifacts if path.stat().st_size == 0]
    if empty:
        raise SaveError(f"空のartifactがあります: {', '.join(empty)}")

    visible_text = outside_fenced_blocks(text)
    pdf_links = WIKI_PDF_RE.findall(visible_text)
    expected_pdf = f"assets/{title}/{title}.pdf"
    if pdf_links != [expected_pdf]:
        raise SaveError(f"PDF埋め込み先が命名規則と一致しません: expected={expected_pdf}")

    artifact_names = {path.name for path in artifacts}
    figure_lines = FIGURE_LINE_RE.findall(extract_frontmatter(text))
    if len(figure_lines) > 1:
        raise SaveError("frontmatterのfigureが重複しています")
    if figure_lines:
        figure_match = FIGURE_RE.fullmatch(figure_lines[0])
        if figure_match is None:
            raise SaveError("frontmatterのfigureは二重引用符で囲んでください")
        figure_path = figure_match.group("path")
        figure_name = Path(figure_path).name
        expected_figure = f"assets/{title}/artifacts/{figure_name}"
        if figure_path != expected_figure:
            raise SaveError(f"figureの参照先が命名規則と一致しません: {figure_path}")
        if figure_name not in artifact_names:
            raise SaveError(f"figureの参照先がartifactsにありません: {figure_path}")

    for link in WIKI_IMAGE_RE.findall(visible_text):
        name = Path(link).name
        expected_image = f"assets/{title}/artifacts/{name}"
        if link != expected_image:
            raise SaveError(f"画像埋め込み先が命名規則と一致しません: {link}")
        if name not in artifact_names:
            raise SaveError(f"画像リンク先がartifactsにありません: {link}")
    if MARKDOWN_IMAGE_RE.search(visible_text):
        raise SaveError("Markdown形式の画像参照が残っています")
    return pdf, artifacts


def save(args: argparse.Namespace) -> tuple[Path, Path, int]:
    markdown = require_nonempty_file(args.markdown, "Markdown")
    text = format_markdown(markdown.read_text(encoding="utf-8"))
    paper_pdf, artifacts = validate_inputs(
        text, args.paper_pdf, args.artifacts_dir, args.sanitized_title
    )
    check_conflicts(args.papers_dir, args.sanitized_title)

    final_note = args.papers_dir / f"{args.sanitized_title}.md"
    final_assets = args.papers_dir / "assets" / args.sanitized_title
    final_pdf = final_assets / f"{args.sanitized_title}.pdf"
    final_artifacts = final_assets / "artifacts"
    note_created = False
    assets_created = False
    artifacts_created = False
    try:
        final_assets.parent.mkdir(exist_ok=True)
        assets_existed = final_assets.exists()
        final_assets.mkdir(exist_ok=True)
        assets_created = not assets_existed
        artifacts_existed = final_artifacts.exists()
        final_artifacts.mkdir(exist_ok=True)
        artifacts_created = not artifacts_existed
        shutil.copy2(paper_pdf, final_pdf)
        for artifact in artifacts:
            shutil.copy2(artifact, final_artifacts / artifact.name)
        with final_note.open("x", encoding="utf-8") as note_file:
            note_created = True
            note_file.write(text)

        require_nonempty_file(final_note, "保存後のMarkdown")
        require_nonempty_file(final_pdf, "保存後のPDF")
        saved = sorted(final_artifacts.glob("*.png"))
        if len(saved) != len(artifacts) or any(path.stat().st_size == 0 for path in saved):
            raise SaveError("保存後のartifact数またはファイルサイズが一致しません")
    except Exception:
        if note_created and final_note.exists():
            final_note.unlink()
        if final_pdf.exists():
            final_pdf.unlink()
        if artifacts_created and final_artifacts.exists():
            shutil.rmtree(final_artifacts)
        if assets_created and final_assets.exists():
            shutil.rmtree(final_assets)
        raise
    return final_note, final_pdf, len(artifacts)


def run(args: argparse.Namespace) -> int:
    if args.check_only:
        check_conflicts(args.papers_dir, args.sanitized_title)
        print("Registration conflicts: none")
        return 0
    final_note, final_pdf, artifact_count = save(args)
    print(f"Markdown: {final_note}")
    print(f"PDF: {final_pdf}")
    print(f"Artifacts: {artifact_count}")
    return 0


def main() -> int:
    try:
        return run(parse_args())
    except (OSError, UnicodeError, SaveError) as exc:
        print(f"paper-save: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

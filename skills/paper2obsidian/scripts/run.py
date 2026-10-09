#!/usr/bin/env python3
"""Whole pipeline in one command: convert, look up publisher data, link, save and verify.

Stops before saving only when Crossref has no record (the agent writes the frontmatter) or OCR was
needed but could not run; <work>/review.md says what to do. After editing <work>/draft.md,
`--resume` links, saves and verifies. Run with Marker's Python:
"$(sed -n '1s/^#!//p' "$(command -v marker_single)")"
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import crossref  # noqa: E402
from link_references import build_note, scalar  # noqa: E402
from paper_common import PaperSaveError, reference_entries, sanitize_title  # noqa: E402
from save_paper import check_conflicts, get_vault_root, save_paper  # noqa: E402

REF_HEADING = re.compile(r"#{1,6}\s+(?:\d+\.?\s+)?(references|bibliography|works cited|参考文献|文献)\s*", re.I)
IMAGE_LINK = re.compile(r"(!\[[^\]]*\]\()([^)\s]+)(\))")
DOI = re.compile(r"\b10\.\d{4,9}/[^\s\"<>\]]+", re.I)
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def split_references(markdown: str) -> tuple[str, str]:
    """Return the draft without its reference section, and that section."""
    # NFKC per line: some PDFs print "参考⽂献" with a Kangxi radical instead of 文.
    offset = 0
    for line in markdown.splitlines(keepends=True):
        if REF_HEADING.fullmatch(unicodedata.normalize("NFKC", line.rstrip("\r\n"))):
            break
        offset += len(line)
    else:
        return markdown, ""
    level = len(markdown[offset:].split(" ", 1)[0])
    rest = markdown[offset + len(line.rstrip("\r\n")):]
    end = re.search(rf"^#{{1,{level}}}\s", rest, re.M)  # next heading of the same or higher level
    return markdown[:offset].rstrip() + "\n\n" + (rest[end.start():] if end else ""), rest[:end.start()] if end else rest


def parse_references(section: str) -> list[dict]:
    """Reference entries with the DOI printed in them, if any."""
    refs = [{"number": e["number"], "raw": e["text"]} for e in reference_entries(section)[1]]
    for ref in refs:
        # Line breaks leave spaces inside DOIs ("doi:10. 48550/arXiv. 2403.02754").
        tail = re.search(r"(?:\bdoi:\s*|doi\.org/)(10\.[\s\S]+)$", ref["raw"], re.I)
        if tail:
            ref["doi"] = re.sub(r"\s+", "", tail[1]).rstrip(".,;>)]")
        elif doi := DOI.search(ref["raw"]):
            ref["doi"] = doi[0].rstrip(".,;>)]")
    return refs


def lookup(args, draft: str, refs: list[dict]) -> tuple[str, list[dict], str]:
    """Frontmatter and tail from Crossref, and the references that can link to notes (DOI + registered title)."""
    if args.offline:
        return draft, [], "none"
    dois = {r["number"]: r["doi"] for r in refs if r.get("doi")}
    headings = [re.sub(r"[#*_]", "", h).strip() for h in re.findall(r"^#{1,6}\s+(.+)$", draft, re.M)]
    status = "none"
    try:
        message, _ = crossref.find_work(args.pdf, headings, args.doi)
        if message:
            try:
                bibtex = crossref.fetch_bibtex(message["DOI"])
            except OSError:
                bibtex = None
            meta = crossref.metadata(message, bibtex)
            # Keep the capitalization printed on the paper (Crossref may lowercase subtitles), unless it is ALL CAPS.
            printed = next((h for h in headings if crossref.title_key(h) == crossref.title_key(meta["title"])), None)
            if printed and printed != printed.upper():
                meta["title"] = printed
            listed, _ = crossref.reference_dois(refs, message)
            dois = listed | dois  # A DOI printed in the entry wins over the list position.
            draft = crossref.frontmatter(meta) + draft.rstrip() + crossref.tail_sections(meta)
            status = "crossref"
        registered = crossref.titles_for_dois(list(dois.values()))
    except (OSError, ValueError, KeyError):
        return draft, [], status
    links = [{"number": n, "doi": d, "title": registered[crossref.doi_key(d)]}
             for n, d in sorted(dois.items()) if crossref.doi_key(d) in registered]
    return draft, links, status


def set_thumbnail(note: str) -> str:
    """The first sizeable image becomes the thumbnail (small ones are logos and icons)."""
    from PIL import Image
    header = FRONTMATTER.match(note)
    if not header or re.search(r"^figure:", header[0], re.M):
        return note
    for _, path, _ in IMAGE_LINK.findall(note[header.end():]):
        try:
            with Image.open(path) as image:
                if min(image.size) < 150:
                    continue
        except OSError:
            continue
        return header[0][:-4] + f"figure: {json.dumps(path, ensure_ascii=False)}\n---\n" + note[header.end():]
    return note


def frontmatter_title(note: str) -> str | None:
    header = FRONTMATTER.match(note)
    return (scalar(header[0], "title") or None) if header else None


def prepare(args, work: Path, vault: Path) -> dict:
    """Convert, look up and write <work>/draft.md. Returns the state saved in <work>/state.json."""
    work.mkdir(parents=True, exist_ok=False)
    extracted = work / "extracted"
    result = subprocess.run([sys.executable, str(SCRIPTS / "convert.py"), str(args.pdf),
                             "--output", str(extracted), "--ocr", args.ocr], capture_output=True, text=True)
    if result.returncode:
        raise PaperSaveError(f"convert.py failed: {(result.stderr or result.stdout).strip()[-800:]}")
    conversion = json.loads(result.stdout.strip().splitlines()[-1])
    # Absolute image paths keep the draft valid wherever it is edited or saved from.
    draft = IMAGE_LINK.sub(lambda m: m[1] + str((extracted / m[2]).resolve()) + m[3],
                           (extracted / "paper.md").read_text(encoding="utf-8"))
    draft, links, metadata = lookup(args, draft, parse_references(split_references(draft)[1]))
    if title := frontmatter_title(draft):
        check_conflicts(vault / "papers", sanitize_title(title))
    (work / "draft.md").write_text(draft, encoding="utf-8")
    (work / "references.json").write_text(json.dumps(links, ensure_ascii=False, indent=1), encoding="utf-8")

    review = []
    if conversion.get("ocr_skipped"):
        review.append("**text**: The text is garbled (" + "; ".join(conversion["ocr_reasons"]) + ") and OCR could "
                      "not run. Tell the user to install llama.cpp (or set LLAMA_CPP_BINARY) and rerun; do not fix it.")
    if metadata == "none":
        import pypdfium2 as pdfium
        page = work / "page-001.png"
        pdfium.PdfDocument(str(args.pdf))[0].render(scale=1.5).to_pil().save(page)
        review.append(f"**metadata**: Crossref has no record. From `{page}`, write the frontmatter (title, authors, "
                      "year, doi, source, citekey) and the ## PDF / ## BibTeX sections.")
    state = {"pdf": str(args.pdf.resolve()), "mode": conversion["mode"], "metadata": metadata, "review": review}
    (work / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    return state


def verify(note_path: Path, pdf_path: Path, work: Path) -> list[str]:
    note = note_path.read_text(encoding="utf-8")
    problems = []
    if str(work) in note or re.search(r"!\[[^\]]*\]\((?!https?:)", note):
        problems.append("note still points at temporary files")
    for embed in re.findall(r"!\[\[([^\]|#]+)", note):
        if not (note_path.parent / embed).is_file():
            problems.append(f"missing embed: {embed}")
    figure = re.search(r'^figure:\s*"([^"]+)"', note, re.M)
    if figure and not (note_path.parent / figure[1]).is_file():
        problems.append(f"missing thumbnail: {figure[1]}")
    if not pdf_path.is_file():
        problems.append("PDF was not saved")
    return problems


def finish(work: Path, state: dict, vault: Path) -> dict:
    draft = (work / "draft.md").read_text(encoding="utf-8")
    title = frontmatter_title(draft)
    if not title:
        raise PaperSaveError("draft.md has no frontmatter title")
    check_conflicts(vault / "papers", sanitize_title(title))
    links = json.loads((work / "references.json").read_text(encoding="utf-8"))
    note, report = build_note(set_thumbnail(draft), links, vault)
    (work / "note.md").write_text(note, encoding="utf-8")
    (work / "links.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    note_path, pdf_path, images = save_paper(vault, title, Path(state["pdf"]), work / "note.md")
    linked = [r for r in report["references"] if not r.get("unlinked")]
    unlinked = [r for r in report["references"] if r.get("unlinked")]
    return {
        "status": "saved", "note": str(note_path), "citekey": scalar(draft, "citekey"), "images": images,
        "mode": state["mode"], "metadata": state["metadata"],
        "references": {"entries": len(report["references"]), "existing": sum(r["exists"] for r in linked),
                       "unsaved": sum(not r["exists"] for r in linked), "unlinked": len(unlinked),
                       "unlinked_with_reason": [r for r in unlinked if r.get("reason")],
                       "missing_numbers": report.get("missing_numbers", []),
                       "duplicate_numbers": report.get("duplicate_numbers", [])},
        "problems": verify(note_path, pdf_path, work),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, nargs="?", help="Input PDF (omit with --resume)")
    parser.add_argument("--work", required=True, type=Path, help="New working directory")
    parser.add_argument("--resume", action="store_true", help="Save after the review.md items were fixed in draft.md")
    parser.add_argument("--vault-root", type=Path, help="Test Vault; otherwise PAPER_SAVE_VAULT_ROOT")
    parser.add_argument("--doi", help="The paper's DOI when page 1 does not print it")
    parser.add_argument("--offline", action="store_true", help="Skip Crossref/doi.org lookups")
    parser.add_argument("--ocr", choices=["auto", "never", "always"], default="auto")
    args = parser.parse_args()
    work = args.work.resolve()
    try:
        vault = args.vault_root.resolve() if args.vault_root else get_vault_root()
        if not vault.is_dir():
            raise PaperSaveError(f"Vault root does not exist: {vault}")
        if args.resume:
            state = json.loads((work / "state.json").read_text(encoding="utf-8"))
        else:
            if not args.pdf or not args.pdf.is_file():
                parser.error("PDF does not exist")
            state = prepare(args, work, vault)
            if state["review"]:
                path = work / "review.md"
                path.write_text(f"# Review\n\nEdit `{work / 'draft.md'}` once for these items, then run with "
                                "`--resume`.\n\n" + "".join(f"- {item}\n" for item in state["review"]), encoding="utf-8")
                print(json.dumps({"status": "review", "review": str(path)}, ensure_ascii=False, indent=1))
                return 2
        print(json.dumps(finish(work, state, vault), ensure_ascii=False, indent=1))
        return 0
    except (OSError, ValueError, PaperSaveError) as exc:
        print(f"paper2obsidian error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
